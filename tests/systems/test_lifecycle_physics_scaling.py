
import pytest
from unittest.mock import MagicMock
from yukkuri_game.game.systems.lifecycle import LifecycleSystem
from yukkuri_game.game.yukkuri_components import YukkuriStats, Needs
from yukkuri_game.game.components import Transform, PhysicsBody
from yukkuri_game.engine.ecs import World
import pymunk

def test_lifecycle_physics_scaling_proportional():
    """
    Test that PhysicsBody radius is scaled proportionally during growth,
    respecting the entity's current size (e.g. for non-standard sized entities).
    """
    # Setup
    world = World()
    settings = MagicMock()
    system = LifecycleSystem(settings)

    entity = world.create_entity()

    # "Giant" Yukkuri.
    # Initially Baby, but huge.
    stats = YukkuriStats(name="Giant", type_id="giant", age=0, growth_stage="Baby")
    needs = Needs(max_health=1000, health=1000)

    # Initial scale 2.0 (so visual size is 2x standard)
    transform = Transform(x=0, y=0, scale=2.0)

    # Physics body should also be larger initially.
    # Radius 20 (instead of standard 10 for Baby)
    body = pymunk.Body(1, 1)
    shape = pymunk.Circle(body, 20.0)
    physics = PhysicsBody(body=body, shape=shape)

    world.add_component(entity, stats)
    world.add_component(entity, needs)
    world.add_component(entity, transform)
    world.add_component(entity, physics)

    # Grow Baby -> Child (scale multiplier 1.5)
    system._grow_entity(world, entity, stats, needs, transform, "Child", 1.5)

    # Visual scale increased correctly
    assert transform.scale == 3.0  # 2.0 * 1.5

    # Verification: Physics radius should be 30.0 (20.0 * 1.5)
    # This confirms the fix that the physics radius scales proportionally.
    assert physics.shape.radius == 30.0
