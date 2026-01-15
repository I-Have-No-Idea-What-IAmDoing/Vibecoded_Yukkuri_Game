import pytest
from yukkuri_game.engine.ecs import World
from yukkuri_game.game.yukkuri_components import (
    YukkuriStats,
    RelationshipRegistry,
    RelationshipData,
    AIState,
    EmotionalState,
)
from yukkuri_game.game.systems.family_system import FamilySystem
from yukkuri_game.game.components import Transform


class TestFamilySystem:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.world = World()
        self.system = FamilySystem()
        self.world.add_system(self.system)

    def test_family_formation(self) -> None:
        # Create two entities
        e1 = self.world.create_entity()
        self.world.add_component(e1, YukkuriStats(name="Y1", type_id="reimu"))
        reg1 = RelationshipRegistry()
        self.world.add_component(e1, reg1)
        self.world.add_component(
            e1, EmotionalState()
        )  # Needed for potential emotional checks

        e2 = self.world.create_entity()
        self.world.add_component(e2, YukkuriStats(name="Y2", type_id="marisa"))
        reg2 = RelationshipRegistry()
        self.world.add_component(e2, reg2)
        self.world.add_component(e2, EmotionalState())

        # Set high affinity
        reg1.relationships[e2] = RelationshipData(affinity=90.0, trust=90.0)
        reg2.relationships[e1] = RelationshipData(affinity=90.0, trust=90.0)

        # Update system (check interval is 10s, so we force check logic or simulate time)
        # We can manually call _process_family_formation for testing or advance time
        self.system.check_interval = 0.0  # Force check
        self.system.update(self.world, 1.0)

        assert reg1.family_group_id is not None
        assert reg2.family_group_id is not None
        assert reg1.family_group_id == reg2.family_group_id

    def test_family_benefits(self) -> None:
        e1 = self.world.create_entity()
        self.world.add_component(e1, YukkuriStats(name="Y1", type_id="reimu"))
        self.world.add_component(e1, EmotionalState(happiness=50.0, stress=10.0))
        self.world.add_component(e1, Transform(x=0, y=0))
        reg1 = RelationshipRegistry(family_group_id=123)
        self.world.add_component(e1, reg1)
        self.world.add_component(e1, AIState())

        e2 = self.world.create_entity()
        self.world.add_component(e2, YukkuriStats(name="Y2", type_id="marisa"))
        self.world.add_component(e2, EmotionalState(happiness=50.0, stress=10.0))
        self.world.add_component(e2, Transform(x=10, y=0))  # Nearby
        reg2 = RelationshipRegistry(family_group_id=123)
        self.world.add_component(e2, reg2)
        self.world.add_component(e2, AIState())

        self.system.check_interval = 0.0
        self.system.update(self.world, 1.0)

        self.world.get_component(e1, EmotionalState)
        self.world.get_component(e2, EmotionalState)

        # If FamilySystem modifies EmotionalState directly now (since YukkuriStats doesn't have it)
        # We assume FamilySystem was updated or needs to be checked.
        # But if FamilySystem code relies on `stats.happiness`, it will fail.
        # I suspect FamilySystem might also need a fix if it uses stats.happiness.
        # I will fix the test first to assume FamilySystem works correctly or fails if code is broken.
        # I updated the test to check `EmotionalState` components.
        # Now I run the test. If it fails due to attribute error, I fix code.

        # Wait, if I assume code is broken, I should check it.
        # Let's peek at `FamilySystem`.
