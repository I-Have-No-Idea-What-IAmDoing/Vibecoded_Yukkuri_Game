import pytest
from src.yukkuri_game.engine.ecs import World
from src.yukkuri_game.game.yukkuri_components import YukkuriStats, RelationshipRegistry, RelationshipData
from src.yukkuri_game.game.systems.family_system import FamilySystem
from src.yukkuri_game.game.components import Transform

class TestFamilySystem:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.world = World()
        self.system = FamilySystem()
        self.world.add_system(self.system)

    def test_family_formation(self):
        # Create two entities
        e1 = self.world.create_entity()
        self.world.add_component(e1, YukkuriStats(name="Y1", type_id="reimu"))
        reg1 = RelationshipRegistry()
        self.world.add_component(e1, reg1)

        e2 = self.world.create_entity()
        self.world.add_component(e2, YukkuriStats(name="Y2", type_id="marisa"))
        reg2 = RelationshipRegistry()
        self.world.add_component(e2, reg2)

        # Set high affinity
        reg1.relationships[e2] = RelationshipData(affinity=90.0, trust=90.0)
        reg2.relationships[e1] = RelationshipData(affinity=90.0, trust=90.0)

        # Update system (check interval is 10s, so we force check logic or simulate time)
        # We can manually call _process_family_formation for testing or advance time
        self.system.check_interval = 0.0 # Force check
        self.system.update(self.world, 1.0)

        assert reg1.family_group_id is not None
        assert reg2.family_group_id is not None
        assert reg1.family_group_id == reg2.family_group_id

    def test_family_benefits(self):
        e1 = self.world.create_entity()
        self.world.add_component(e1, YukkuriStats(name="Y1", type_id="reimu", happiness=50.0, stress=10.0))
        self.world.add_component(e1, Transform(x=0, y=0))
        reg1 = RelationshipRegistry(family_group_id=123)
        self.world.add_component(e1, reg1)

        e2 = self.world.create_entity()
        self.world.add_component(e2, YukkuriStats(name="Y2", type_id="marisa", happiness=50.0, stress=10.0))
        self.world.add_component(e2, Transform(x=10, y=0)) # Nearby
        reg2 = RelationshipRegistry(family_group_id=123)
        self.world.add_component(e2, reg2)

        self.system.check_interval = 0.0
        self.system.update(self.world, 1.0)

        s1 = self.world.get_component(e1, YukkuriStats)
        s2 = self.world.get_component(e2, YukkuriStats)

        assert s1.happiness > 50.0
        assert s1.stress < 10.0
        assert s2.happiness > 50.0
        assert s2.stress < 10.0
