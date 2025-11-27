import pytest
from yukkuri_game.engine.ecs import World, System, Component

# Define some simple components for testing
class Position(Component):
    def __init__(self, x, y):
        self.x = x
        self.y = y

class Velocity(Component):
    def __init__(self, vx, vy):
        self.vx = vx
        self.vy = vy

class Health(Component):
    def __init__(self, hp):
        self.hp = hp

# Define a simple system for testing
class MovementSystem(System):
    def update(self, world: World, dt: float) -> None:
        entities = world.get_entities_with(Position, Velocity)
        for entity in entities:
            pos = world.get_component(entity, Position)
            vel = world.get_component(entity, Velocity)
            pos.x += vel.vx * dt
            pos.y += vel.vy * dt

def test_create_destroy_entity():
    world = World()
    entity1 = world.create_entity()
    entity2 = world.create_entity()

    assert entity1 != entity2
    assert world.entity_exists(entity1)
    assert world.entity_exists(entity2)

    world.destroy_entity(entity1)
    assert not world.entity_exists(entity1)
    assert world.entity_exists(entity2)

def test_add_get_remove_component():
    world = World()
    entity = world.create_entity()

    pos = Position(10, 20)
    world.add_component(entity, pos)

    assert world.has_component(entity, Position)
    assert world.get_component(entity, Position) == pos

    world.remove_component(entity, Position)
    assert not world.has_component(entity, Position)
    assert world.get_component(entity, Position) is None

def test_get_entities_with():
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

def test_system_update():
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
    assert pos1.x == 5.0 # 0 + 10 * 0.5
    assert pos1.y == 2.5 # 0 + 5 * 0.5

    pos2 = world.get_component(e2, Position)
    assert pos2.x == 10
    assert pos2.y == 10

def test_get_components():
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
