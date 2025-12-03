import pymunk
from yukkuri_game.engine.ecs import World
from yukkuri_game.engine.event_bus import EventBus
from yukkuri_game.game.systems.physics import PhysicsSystem
from yukkuri_game.game.components import Transform, PhysicsBody


def test_physics_body_cleanup():
    world = World()
    event_bus = EventBus()
    world.services.register(event_bus)

    physics_system = PhysicsSystem()
    world.add_system(physics_system)

    # Create entity
    e1 = world.create_entity()

    # Add physics components manually (simulating factory)
    body = pymunk.Body(1, 1)
    shape = pymunk.Circle(body, 10)
    physics_system.space.add(body, shape)

    world.add_component(e1, PhysicsBody(body=body, shape=shape))
    world.add_component(e1, Transform(0, 0))

    assert len(physics_system.space.bodies) == 1

    # Run one update to ensure system is initialized (lazy subs)
    physics_system.update(world, 0.1)

    # Destroy entity
    world.destroy_entity(e1)

    # Check if body was removed from space
    assert len(physics_system.space.bodies) == 0


if __name__ == "__main__":
    test_physics_body_cleanup()
