import pytest
from unittest.mock import Mock
from yukkuri_game.engine.ecs import World
from yukkuri_game.engine.components import Transform, PhysicsBody
from yukkuri_game.game.components import YukkuriStats, ItemStats, Poop
from yukkuri_game.game.systems.physics_reconstruction import reconstruct_physics
from yukkuri_game.engine.resource_manager import ResourceManager
from yukkuri_game.game.collision_constants import CollisionCategories
from yukkuri_game.engine.systems.physics import PhysicsSystem
from yukkuri_game.engine.protocols import IPhysicsService


@pytest.fixture
def mock_physics_system(monkeypatch):
    ps = Mock(spec=PhysicsSystem)
    ps.space = Mock()  # Mock pymunk space
    # The real physics system constructor might do complex things, so we mock it.
    return ps


def test_reconstruct_physics_yukkuri(mock_physics_system):
    world = World()
    world.services.register(mock_physics_system, IPhysicsService)

    # Create entity with stats but no physics body
    entity = world.create_entity()
    world.add_component(entity, Transform(x=100, y=100))
    world.add_component(
        entity, YukkuriStats(name="Test", type_id="test", growth_stage=1)
    )  # Adult size

    # Run reconstruction
    reconstruct_physics(world)

    # Check if PhysicsBody was added
    assert world.has_component(entity, PhysicsBody)
    body_comp = world.get_component(entity, PhysicsBody)
    assert body_comp.body.position == (100, 100)
    assert body_comp.shape.filter.categories == CollisionCategories.GROUND_UNIT

    # Run again, should not double add (implicit check, pymunk might error or we just check count if we could)
    # But since PhysicsBody is unique component per entity in ECS usually, checking existence is enough.
    # The function explicitly checks `if world.has_component(entity, PhysicsBody): continue`

    # Store old body
    old_body = body_comp
    reconstruct_physics(world)
    assert world.get_component(entity, PhysicsBody) is old_body


def test_reconstruct_physics_poop(mock_physics_system):
    world = World()
    world.services.register(mock_physics_system, IPhysicsService)
    entity = world.create_entity()
    world.add_component(entity, Transform(x=50, y=50))
    world.add_component(entity, Poop())

    reconstruct_physics(world)

    assert world.has_component(entity, PhysicsBody)
    body_comp = world.get_component(entity, PhysicsBody)
    assert body_comp.body.position == (50, 50)
    assert body_comp.shape.filter.categories == CollisionCategories.POOP


def test_reconstruct_physics_item(mock_physics_system):
    world = World()
    world.services.register(mock_physics_system, IPhysicsService)

    # Mock ResourceManager for item dimensions
    rm = Mock(spec=ResourceManager)
    rm.item_types = {"cookie": {"width": 64, "height": 64}}
    world.services.register(rm, ResourceManager)

    entity = world.create_entity()
    world.add_component(entity, Transform(x=200, y=200))
    world.add_component(entity, ItemStats(name="Cookie", type_id="cookie", cost=10))

    reconstruct_physics(world)

    assert world.has_component(entity, PhysicsBody)
    body_comp = world.get_component(entity, PhysicsBody)
    assert body_comp.body.position == (200, 200)
    assert body_comp.shape.filter.categories == CollisionCategories.ITEM

    # Check if dimensions were used (Box shape)
    # Pymunk Poly shape for box
    import pymunk

    assert isinstance(body_comp.shape, pymunk.Poly)


def test_reconstruct_physics_item_default_size(mock_physics_system):
    world = World()
    world.services.register(mock_physics_system, IPhysicsService)
    # No resource manager registered, should fallback to defaults

    entity = world.create_entity()
    world.add_component(entity, Transform(x=300, y=300))
    world.add_component(entity, ItemStats(name="Unknown", type_id="unknown", cost=1))

    reconstruct_physics(world)

    assert world.has_component(entity, PhysicsBody)


def test_reconstruct_physics_item_obstacle(mock_physics_system):
    world = World()
    world.services.register(mock_physics_system, IPhysicsService)

    # Mock ResourceManager using SimpleNamespace to support getattr
    from types import SimpleNamespace
    rm = Mock(spec=ResourceManager)
    rm.item_types = {"wall": SimpleNamespace(width=32, height=32, obstacle_type="HIGH")}
    world.services.register(rm, ResourceManager)

    # Mock NavigationService
    from yukkuri_game.game.ai.navigation_service import NavigationService
    from yukkuri_game.game.ai.navigation_service import ObstacleType
    nav_service = Mock(spec=NavigationService)
    world.services.register(nav_service, NavigationService)

    entity = world.create_entity()
    world.add_component(entity, Transform(x=150, y=150))
    world.add_component(entity, ItemStats(name="Wall", type_id="wall", cost=5))

    reconstruct_physics(world)

    assert world.has_component(entity, PhysicsBody)
    nav_service.update_obstacle_rect.assert_called_once_with(
        150.0, 150.0, 32.0, 32.0, walkable=False, obstacle_type=ObstacleType.HIGH
    )
