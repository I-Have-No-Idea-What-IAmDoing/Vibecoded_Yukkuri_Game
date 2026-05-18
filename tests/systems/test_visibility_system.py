import pymunk
from yukkuri_game.engine.ecs import World
from yukkuri_game.game.systems.visibility_system import VisibilitySystem
from yukkuri_game.engine.systems.physics import PhysicsSystem
from yukkuri_game.game.components import Vision
from yukkuri_game.engine.components import PhysicsBody, Transform
from yukkuri_game.game.components import AIState
from yukkuri_game.game.collision_constants import CollisionCategories


def test_visibility_occlusion():
    from tests.test_utils import make_configured_world
    world = make_configured_world()

    physics_system = PhysicsSystem()
    world.services.register(physics_system, PhysicsSystem)
    world.add_system(physics_system)

    from yukkuri_game.engine.systems.spatial import SpatialSystem, SpatialService
    from yukkuri_game.engine.event_bus import EventBus
    event_bus = world.services.get(EventBus)
    spatial_system = SpatialSystem(event_bus=event_bus)
    world.services.register(spatial_system.spatial_service, SpatialService)
    world.add_system(spatial_system)
    world.add_system(physics_system)

    vis_system = VisibilitySystem()
    world.add_system(vis_system)

    # Observer (Yukkuri) at (0, 0)
    obs = world.create_entity()
    obs_body = pymunk.Body(body_type=pymunk.Body.KINEMATIC)
    obs_body.position = (0, 0)
    obs_shape = pymunk.Circle(obs_body, 10)
    obs_shape.filter = pymunk.ShapeFilter(categories=CollisionCategories.GROUND_UNIT)
    physics_system.space.add(obs_body, obs_shape)

    world.add_component(obs, PhysicsBody(body=obs_body, shape=obs_shape))
    world.add_component(obs, Transform(x=0, y=0))
    world.add_component(obs, Vision(range=200, fov=360))
    world.add_component(obs, AIState())

    # Target (Yukkuri) at (100, 0) - Visible
    target1 = world.create_entity()
    t1_body = pymunk.Body(body_type=pymunk.Body.KINEMATIC)
    t1_body.position = (100, 0)
    t1_shape = pymunk.Circle(t1_body, 10)
    t1_shape.filter = pymunk.ShapeFilter(categories=CollisionCategories.GROUND_UNIT)
    physics_system.space.add(t1_body, t1_shape)

    world.add_component(target1, PhysicsBody(body=t1_body, shape=t1_shape))
    world.add_component(target1, Transform(x=100, y=0))

    # Target 2 (Yukkuri) at (200, 0) - Behind Wall - Occluded
    target2 = world.create_entity()
    t2_body = pymunk.Body(body_type=pymunk.Body.KINEMATIC)
    t2_body.position = (200, 0)
    t2_shape = pymunk.Circle(t2_body, 10)
    t2_shape.filter = pymunk.ShapeFilter(categories=CollisionCategories.GROUND_UNIT)
    physics_system.space.add(t2_body, t2_shape)

    world.add_component(target2, PhysicsBody(body=t2_body, shape=t2_shape))
    world.add_component(target2, Transform(x=200, y=0))

    # Wall between 150, -50 and 150, 50
    wall_body = pymunk.Body(body_type=pymunk.Body.STATIC)
    wall_body.position = (150, 0)
    wall_shape = pymunk.Segment(wall_body, (0, -50), (0, 50), 5)
    wall_shape.filter = pymunk.ShapeFilter(categories=CollisionCategories.HIGH_OBSTACLE)
    physics_system.space.add(wall_body, wall_shape)

    # Update
    spatial_system.update(world, 0.1)
    vis_system.update(world, 0.1)

    # Check
    ai = world.get_component(obs, AIState)
    assert target1 in ai.visible_entities
    assert target2 not in ai.visible_entities


def test_visibility_fov():
    from tests.test_utils import make_configured_world
    world = make_configured_world()
    physics_system = PhysicsSystem()
    world.services.register(physics_system, PhysicsSystem)
    world.add_system(physics_system)

    from yukkuri_game.engine.systems.spatial import SpatialSystem, SpatialService
    from yukkuri_game.engine.event_bus import EventBus
    event_bus = world.services.get(EventBus)
    spatial_system = SpatialSystem(event_bus=event_bus)
    world.services.register(spatial_system.spatial_service, SpatialService)
    world.add_system(spatial_system)
    world.add_system(physics_system)
    vis_system = VisibilitySystem()
    world.add_system(vis_system)

    # Observer facing East (1, 0) -> Angle 0
    obs = world.create_entity()
    obs_body = pymunk.Body(body_type=pymunk.Body.KINEMATIC)
    obs_body.position = (0, 0)
    obs_body.angle = 0
    obs_shape = pymunk.Circle(obs_body, 10)
    obs_shape.filter = pymunk.ShapeFilter(categories=CollisionCategories.GROUND_UNIT)
    physics_system.space.add(obs_body, obs_shape)

    world.add_component(obs, PhysicsBody(body=obs_body, shape=obs_shape))
    world.add_component(obs, Transform(x=0, y=0, rotation=0))
    world.add_component(obs, Vision(range=200, fov=90))  # 90 degree FOV (+- 45)
    world.add_component(obs, AIState())

    # Target In Front
    t1 = world.create_entity()
    t1b = pymunk.Body(body_type=pymunk.Body.KINEMATIC)
    t1b.position = (100, 0)
    t1s = pymunk.Circle(t1b, 10)
    t1s.filter = pymunk.ShapeFilter(categories=CollisionCategories.GROUND_UNIT)
    physics_system.space.add(t1b, t1s)
    world.add_component(t1, PhysicsBody(body=t1b, shape=t1s))
    world.add_component(t1, Transform(x=100, y=0))

    # Target Behind
    t2 = world.create_entity()
    t2b = pymunk.Body(body_type=pymunk.Body.KINEMATIC)
    t2b.position = (-100, 0)
    t2s = pymunk.Circle(t2b, 10)
    t2s.filter = pymunk.ShapeFilter(categories=CollisionCategories.GROUND_UNIT)
    physics_system.space.add(t2b, t2s)
    world.add_component(t2, PhysicsBody(body=t2b, shape=t2s))
    world.add_component(t2, Transform(x=-100, y=0))

    spatial_system.update(world, 0.1)
    vis_system.update(world, 0.1)

    ai = world.get_component(obs, AIState)
    assert t1 in ai.visible_entities
    assert t2 not in ai.visible_entities


def test_visibility_non_physics_entity_is_visible():
    """Regression: entities without a PhysicsBody (items, food) must be visible.

    Before the fix, `if hit:` was the only path to `visible.add()`, so any
    entity whose raycast returned None (no physics shape to hit) was silently
    dropped from the visible set — making all non-physics entities invisible.
    """
    from tests.test_utils import make_configured_world

    world = make_configured_world()
    physics_system = PhysicsSystem()
    world.services.register(physics_system, PhysicsSystem)
    world.add_system(physics_system)

    from yukkuri_game.engine.systems.spatial import SpatialSystem, SpatialService
    from yukkuri_game.engine.event_bus import EventBus

    event_bus = world.services.get(EventBus)
    spatial_system = SpatialSystem(event_bus=event_bus)
    world.services.register(spatial_system.spatial_service, SpatialService)
    world.add_system(spatial_system)

    vis_system = VisibilitySystem()
    world.add_system(vis_system)

    # Observer with physics body at origin.
    obs = world.create_entity()
    obs_body = pymunk.Body(body_type=pymunk.Body.KINEMATIC)
    obs_body.position = (0, 0)
    obs_shape = pymunk.Circle(obs_body, 10)
    obs_shape.filter = pymunk.ShapeFilter(
        categories=CollisionCategories.GROUND_UNIT
    )
    physics_system.space.add(obs_body, obs_shape)
    world.add_component(obs, PhysicsBody(body=obs_body, shape=obs_shape))
    world.add_component(obs, Transform(x=0, y=0))
    world.add_component(obs, Vision(range=300, fov=360))
    world.add_component(obs, AIState())

    # Item entity: Transform only, NO PhysicsBody — simulates food / loot.
    item = world.create_entity()
    world.add_component(item, Transform(x=100, y=0))

    spatial_system.update(world, 0.1)
    vis_system.update(world, 0.1)

    ai = world.get_component(obs, AIState)
    assert item in ai.visible_entities, (
        "Non-physics entity within vision range must be in visible_entities"
    )


def test_visibility_wall_blocks_physics_entity():
    """Regression: a static wall (no userdata) must still block LoS.

    A static wall body created by the level editor has body.userdata = None.
    Ensure the visibility system correctly occludes targets behind such walls.
    """
    from tests.test_utils import make_configured_world

    world = make_configured_world()
    physics_system = PhysicsSystem()
    world.services.register(physics_system, PhysicsSystem)
    world.add_system(physics_system)

    from yukkuri_game.engine.systems.spatial import SpatialSystem, SpatialService
    from yukkuri_game.engine.event_bus import EventBus

    event_bus = world.services.get(EventBus)
    spatial_system = SpatialSystem(event_bus=event_bus)
    world.services.register(spatial_system.spatial_service, SpatialService)
    world.add_system(spatial_system)

    vis_system = VisibilitySystem()
    world.add_system(vis_system)

    # Observer.
    obs = world.create_entity()
    obs_body = pymunk.Body(body_type=pymunk.Body.KINEMATIC)
    obs_body.position = (0, 0)
    obs_shape = pymunk.Circle(obs_body, 10)
    obs_shape.filter = pymunk.ShapeFilter(
        categories=CollisionCategories.GROUND_UNIT
    )
    physics_system.space.add(obs_body, obs_shape)
    world.add_component(obs, PhysicsBody(body=obs_body, shape=obs_shape))
    world.add_component(obs, Transform(x=0, y=0))
    world.add_component(obs, Vision(range=500, fov=360))
    world.add_component(obs, AIState())

    # Wall at x=150 with no userdata (simulates level geometry).
    wall_body = pymunk.Body(body_type=pymunk.Body.STATIC)
    # userdata intentionally left as None
    wall_shape = pymunk.Segment(wall_body, (150, -50), (150, 50), 5)
    wall_shape.filter = pymunk.ShapeFilter(
        categories=CollisionCategories.HIGH_OBSTACLE
    )
    physics_system.space.add(wall_body, wall_shape)

    # Target behind the wall.
    target = world.create_entity()
    t_body = pymunk.Body(body_type=pymunk.Body.KINEMATIC)
    t_body.position = (300, 0)
    t_shape = pymunk.Circle(t_body, 10)
    t_shape.filter = pymunk.ShapeFilter(
        categories=CollisionCategories.GROUND_UNIT
    )
    physics_system.space.add(t_body, t_shape)
    world.add_component(target, PhysicsBody(body=t_body, shape=t_shape))
    world.add_component(target, Transform(x=300, y=0))

    spatial_system.update(world, 0.1)
    vis_system.update(world, 0.1)

    ai = world.get_component(obs, AIState)
    assert target not in ai.visible_entities, (
        "Target behind a wall (no userdata) must be blocked"
    )
