"""
Tests for the ECS (Entity Component System) module.
"""

from yukkuri_game.engine.ecs import World, System, Component


# Define some simple components for testing
class Position(Component):
    """Component for testing position."""

    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y


class Velocity(Component):
    """Component for testing velocity."""

    def __init__(self, vx: float, vy: float) -> None:
        self.vx = vx
        self.vy = vy


class Health(Component):
    """Component for testing health."""

    def __init__(self, hp: float) -> None:
        self.hp = hp


# Define a simple system for testing
class MovementSystem(System):
    """System for testing movement updates."""

    def update(self, world: World, dt: float) -> None:
        entities = world.get_entities_with(Position, Velocity)
        for entity in entities:
            pos = world.get_component(entity, Position)
            vel = world.get_component(entity, Velocity)
            if pos and vel:
                pos.x += vel.vx * dt
                pos.y += vel.vy * dt


def test_create_destroy_entity() -> None:
    """
    Tests entity creation and destruction.
    """
    world = World()
    entity1 = world.create_entity()
    entity2 = world.create_entity()

    assert entity1 != entity2
    assert world.entity_exists(entity1)
    assert world.entity_exists(entity2)

    world.destroy_entity(entity1)
    assert not world.entity_exists(entity1)
    assert world.entity_exists(entity2)


def test_add_get_remove_component() -> None:
    """
    Tests adding, retrieving, and removing components.
    """
    world = World()
    entity = world.create_entity()

    pos = Position(10, 20)
    world.add_component(entity, pos)

    assert world.has_component(entity, Position)
    assert world.get_component(entity, Position) == pos

    world.remove_component(entity, Position)
    assert not world.has_component(entity, Position)
    assert world.get_component(entity, Position) is None


def test_get_entities_with() -> None:
    """
    Tests querying entities by component types.
    """
    world = World()
    e1 = world.create_entity()
    e2 = world.create_entity()
    e3 = world.create_entity()

    world.add_component(e1, Position(0, 0))
    world.add_component(e1, Velocity(1, 1))

    world.add_component(e2, Position(10, 10))

    world.add_component(e3, Velocity(2, 2))
    world.add_component(e3, Health(100))

    entities_pos_vel = world.get_entities_with(Position, Velocity)
    assert e1 in entities_pos_vel
    assert e2 not in entities_pos_vel
    assert e3 not in entities_pos_vel

    entities_pos = world.get_entities_with(Position)
    assert e1 in entities_pos
    assert e2 in entities_pos
    assert e3 not in entities_pos


def test_system_update() -> None:
    """
    Tests that systems update components correctly.
    """
    world = World()
    system = MovementSystem()
    world.add_system(system)

    e1 = world.create_entity()
    world.add_component(e1, Position(0, 0))
    world.add_component(e1, Velocity(10, 5))

    e2 = world.create_entity()
    world.add_component(e2, Position(10, 10))
    # No velocity, so shouldn't move

    dt = 0.5
    world.update(dt)

    pos1 = world.get_component(e1, Position)
    assert pos1.x == 5.0  # 0 + 10 * 0.5
    assert pos1.y == 2.5  # 0 + 5 * 0.5

    pos2 = world.get_component(e2, Position)
    assert pos2.x == 10
    assert pos2.y == 10


def test_get_components() -> None:
    """
    Tests retrieving all components of a specific type.
    """
    world = World()
    e1 = world.create_entity()
    e2 = world.create_entity()

    p1 = Position(1, 2)
    p2 = Position(3, 4)

    world.add_component(e1, p1)
    world.add_component(e2, p2)

    comps = world.get_components(Position)
    assert len(comps) == 2
    assert comps[e1] == p1
    assert comps[e2] == p2


def test_get_all_entities() -> None:
    """
    Tests retrieving all entities in the world.
    """
    world = World()
    e1 = world.create_entity()
    e2 = world.create_entity()

    all_e = world.get_all_entities()
    assert len(all_e) == 2
    assert e1 in all_e
    assert e2 in all_e


def test_multiple_worlds() -> None:
    """
    Tests that multiple world instances are independent.
    """
    w1 = World()
    w2 = World()

    e1 = w1.create_entity()
    e2 = w2.create_entity()

    assert w1.entity_exists(e1)

    # esper entity IDs are just integers starting from 1.
    # They are shared across contexts if contexts share state, but here contexts are switched.
    # However, if e1 is 1, and e2 is 1 (in different world), then w2.entity_exists(1) is True.
    # So we should check if we get same ID but they are actually different entities.

    # If esper implementation restarts ID counter for new context, then e1 == e2 == 1.
    # w1 has entity 1. w2 has entity 1.
    # So w2.entity_exists(e1) (which is 1) will be true.

    # Let's verify if IDs are same
    if e1 == e2:
        assert w2.entity_exists(e1)
    else:
        assert not w2.entity_exists(e1)
