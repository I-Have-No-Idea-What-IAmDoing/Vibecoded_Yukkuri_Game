import pytest
from yukkuri_game.engine.ecs import World, System, Component

class ComponentA(Component):
    pass

class ComponentB(Component):
    pass

class TestSystem(System):
    def __init__(self):
        self.updated = False
        self.dt = 0.0

    def update(self, world, dt):
        self.updated = True
        self.dt = dt

class TestWorld:
    def test_entity_creation_destruction(self):
        world = World()
        e1 = world.create_entity()
        assert world.entity_exists(e1)

        world.destroy_entity(e1)
        assert not world.entity_exists(e1)

        # Destroy non-existent
        world.destroy_entity(e1) # Should not raise

    def test_components(self):
        world = World()
        e1 = world.create_entity()
        c1 = ComponentA()

        world.add_component(e1, c1)
        assert world.has_component(e1, ComponentA)
        assert world.get_component(e1, ComponentA) is c1

        world.remove_component(e1, ComponentA)
        assert not world.has_component(e1, ComponentA)
        assert world.get_component(e1, ComponentA) is None

        # Remove non-existent
        world.remove_component(e1, ComponentB) # Should not raise

    def test_get_components(self):
        world = World()
        e1 = world.create_entity(ComponentA())
        e2 = world.create_entity(ComponentA(), ComponentB())
        e3 = world.create_entity(ComponentB())

        comps_a = world.get_components(ComponentA)
        assert len(comps_a) == 2
        assert e1 in comps_a
        assert e2 in comps_a

        entities_ab = world.get_entities_with(ComponentA, ComponentB)
        assert len(entities_ab) == 1
        assert entities_ab[0] == e2

        # Test empty
        assert len(world.get_entities_with()) == 0

        tuples = world.get_components_tuple(ComponentA, ComponentB)
        assert len(tuples) == 1
        assert tuples[0][0] == e2

    def test_get_all_entities(self):
        world = World()
        e1 = world.create_entity()
        e2 = world.create_entity()

        all_e = world.get_all_entities()
        assert len(all_e) == 2
        assert e1 in all_e
        assert e2 in all_e

    def test_systems(self):
        world = World()
        system = TestSystem()
        world.add_system(system)

        world.update(0.5)
        assert system.updated
        assert system.dt == 0.5

    def test_multiple_worlds(self):
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
