"""Tests for the BevyWorldAdapter and behavior FFI entry point."""

from yukkuri_game.game.systems.behavior_ffi import BevyWorldAdapter
from yukkuri_game.game.systems.behavior_ffi import tick_entity_with_blackboard
from yukkuri_game.engine.components import Transform
from yukkuri_game.game.components import Needs
from yukkuri_game.game.components import AIState
from yukkuri_game.game.components import YukkuriStats
from yukkuri_game.game.components.social import Blackboard as PyBlackboard
from yukkuri_game.engine.components import Flight
from yukkuri_game.game.components import EmotionalState
from yukkuri_game.game.components import ItemStats


class DummyTargetInfo:
    """Mock target info structure matching Rust TargetInfo."""

    def __init__(
        self,
        entity_id: int,
        type_id: str,
        growth_stage: str,
        x: float,
        y: float,
        distance: float,
        affinity: float,
        is_threat: bool,
        is_prey: bool,
        is_family: bool,
        tags: list[str],
    ) -> None:
        """Initializes DummyTargetInfo.

        Args:
            entity_id: Entity ID.
            type_id: Archetype ID.
            growth_stage: Growth stage.
            x: Target X position.
            y: Target Y position.
            distance: Distance to target.
            affinity: Affinity rating.
            is_threat: Threat flag.
            is_prey: Prey flag.
            is_family: Family flag.
            tags: Set of tags.
        """
        self.entity_id = entity_id
        self.type_id = type_id
        self.growth_stage = growth_stage
        self.x = x
        self.y = y
        self.distance = distance
        self.affinity = affinity
        self.is_threat = is_threat
        self.is_prey = is_prey
        self.is_family = is_family
        self.tags = tags


class DummyBlackboard:
    """Mock blackboard structure matching Rust Blackboard."""

    def __init__(self) -> None:
        """Initializes DummyBlackboard."""
        self.entity_id: int = 42
        self.x: float = 150.0
        self.y: float = 250.0
        self.altitude: float = 10.0
        self.flight_state: int = 2
        self.type_id: str = "reimu"
        self.growth_stage: str = "Adult"
        self.current_action: str = "Wander"
        self.stats: dict[str, float] = {
            "health": 90.0,
            "hunger": 10.0,
            "social": 45.0,
            "energy": 80.0,
            "cleanliness": 95.0,
            "bladder": 5.0,
            "easiness": 50.0,
            "max_health": 100.0,
            "happiness": 75.0,
            "stress": 20.0,
            "stamina": 60.0,
        }
        self.visible_targets: list[DummyTargetInfo] = [
            DummyTargetInfo(
                entity_id=100,
                type_id="marisa",
                growth_stage="Adult",
                x=180.0,
                y=250.0,
                distance=30.0,
                affinity=60.0,
                is_threat=False,
                is_prey=False,
                is_family=False,
                tags=["yukkuri"],
            ),
            DummyTargetInfo(
                entity_id=101,
                type_id="food",
                growth_stage="None",
                x=150.0,
                y=280.0,
                distance=30.0,
                affinity=0.0,
                is_threat=False,
                is_prey=False,
                is_family=False,
                tags=["Food", "Item"],
            ),
        ]
        self.short_term_memory: dict[int, tuple[float, float, float]] = {
            200: (120.0, 130.0, 1.5)
        }
        self.grid_width: int = 10
        self.grid_height: int = 10
        self.grid_cells: list[int] = [1] * 100

    def is_walkable(self, gx: int, gy: int, capability: int) -> bool:
        """Mock walkability check."""
        return True


def test_bevy_world_adapter_components() -> None:
    """Verifies BevyWorldAdapter retrieves correctly mapped components."""
    blackboard = DummyBlackboard()
    adapter = BevyWorldAdapter(blackboard)

    # 1. Transform component mapping
    transform = adapter.try_get_component(42, Transform)
    assert transform is not None
    assert transform.x == 150.0
    assert transform.y == 250.0

    # 2. Needs component mapping
    needs = adapter.try_get_component(42, Needs)
    assert needs is not None
    assert needs.health == 90.0
    assert needs.hunger == 10.0
    assert needs.energy == 80.0
    assert needs.max_health == 100.0

    # 3. YukkuriStats mapping
    stats = adapter.try_get_component(42, YukkuriStats)
    assert stats is not None
    assert stats.type_id == "reimu"
    assert stats.growth_stage == "Adult"

    # 4. Flight component mapping
    flight = adapter.try_get_component(42, Flight)
    assert flight is not None
    assert flight.altitude == 10.0
    assert flight.stamina == 60.0

    # 5. EmotionalState mapping
    emotions = adapter.try_get_component(42, EmotionalState)
    assert emotions is not None
    assert emotions.happiness == 75.0
    assert emotions.stress == 20.0

    # 6. Blackboard mapping
    py_bb = adapter.try_get_component(42, PyBlackboard)
    assert py_bb is not None
    assert len(py_bb.visible_targets) == 2
    assert 100 in py_bb.visible_targets
    assert py_bb.visible_targets[100].relation == "Friend"
    assert py_bb.visible_targets[101].relation == "Neutral"
    assert py_bb.closest_food_id == 101


def test_bevy_world_adapter_services() -> None:
    """Verifies BevyWorldAdapter mocks retrieve service locator calls."""
    blackboard = DummyBlackboard()
    adapter = BevyWorldAdapter(blackboard)

    # Test TimeService mock
    from yukkuri_game.engine.services.time_service import TimeService
    time_svc = adapter.services.try_get(TimeService)
    assert time_svc is not None
    assert time_svc.day == 1

    # Test GameService mock
    from yukkuri_game.game.services import GameService
    game_svc = adapter.services.try_get(GameService)
    assert game_svc is not None
    best_item = game_svc.find_best_item((150.0, 250.0), "nutrition")
    assert best_item == 101

    # Test ISpatialService mock
    from yukkuri_game.engine.protocols import ISpatialService
    spatial_svc = adapter.services.try_get(ISpatialService)
    assert spatial_svc is not None
    nearest = spatial_svc.get_nearest_entity(
        adapter, 150.0, 250.0, component_filter=ItemStats
    )
    assert nearest == 101


def test_tick_entity_with_blackboard() -> None:
    """Verifies ticking entrypoint runs behavior tree and returns commands."""
    blackboard = DummyBlackboard()
    commands = tick_entity_with_blackboard(blackboard)
    assert isinstance(commands, list)
    assert len(commands) > 0
    cmd = commands[0]
    assert cmd.entity_id == 42
    assert "target_x" in cmd.payload


def test_tick_entity_with_blackboard_caching_closures() -> None:
    """Verifies that closures capture the updated world adapter state."""
    # First tick: Wander goal
    bb1 = DummyBlackboard()
    bb1.entity_id = 1234
    bb1.current_action = "Wander"
    tick_entity_with_blackboard(bb1)

    # Verify that the adapter was cached
    from yukkuri_game.game.systems.behavior_ffi import (
        _world_adapters,
        _behavior_trees,
    )
    assert 1234 in _world_adapters
    assert 1234 in _behavior_trees

    # Verify that first tick state has AIState current_action as Wander
    adapter = _world_adapters[1234]
    ai_state1 = adapter.try_get_component(1234, AIState)
    assert ai_state1 is not None
    assert ai_state1.current_action == "Wander"

    # Second tick: Eat goal
    bb2 = DummyBlackboard()
    bb2.entity_id = 1234
    bb2.current_action = "Eat"
    tick_entity_with_blackboard(bb2)

    # Verify the cached adapter's blackboard has updated
    assert adapter.blackboard.current_action == "Eat"

    # Verify that the AIState component now returns Eat
    ai_state2 = adapter.try_get_component(1234, AIState)
    assert ai_state2 is not None
    assert ai_state2.current_action == "Eat"

