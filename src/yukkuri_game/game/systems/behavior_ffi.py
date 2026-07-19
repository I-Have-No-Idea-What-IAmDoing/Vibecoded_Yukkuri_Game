"""FFI integration module for Bevy-Rust embedded python execution.

Provides the BevyWorldAdapter to mock the esper World interface and
the entry point for ticking behavior trees with Rust Blackboard snapshots.
"""

from typing import Any
import pymunk
from ...engine.components import Transform
from ...engine.components import MovementController
from ...engine.components import Flight
from ...engine.components import FlightState
from ...engine.components import Mount
from ..components import AIState
from ..components import ItemStats
from ..components import Predator
from ..components import YukkuriStats
from ..components import Needs
from ..components import EmotionalState
from ..components.inventory import InventoryComponent, ItemStack
from ..components.social import Blackboard as PyBlackboard
from ..components.social import TargetInfo as PyTargetInfo
from ..components.social import LastKnownPosition as PyLastKnownPosition
from ..ai.commands import CommandQueue as PyCommandQueue
from ..ai.commands import CommandType as PyCommandType
from ..ai.commands import Command as PyCommand
from ..ai.behaviors import create_yukkuri_behavior_tree
from ..components.social import Personality, PersonalityAxis
from ..components import Skills, SkillState


class FfiNeeds(Needs):
    """FFI proxy for Needs to intercept mutations and queue commands."""

    def __init__(self, world_adapter: Any, entity_id: int, *args: Any, **kwargs: Any) -> None:
        object.__setattr__(self, "_initialized", False)
        super().__init__(*args, **kwargs)
        object.__setattr__(self, "_world_adapter", world_adapter)
        object.__setattr__(self, "_entity_id", entity_id)
        object.__setattr__(self, "_initialized", True)

    def __setattr__(self, name: str, value: Any) -> None:
        if getattr(self, "_initialized", False) and name not in (
            "_initialized",
            "_world_adapter",
            "_entity_id",
        ):
            old_val = getattr(self, name, 0.0)
            super().__setattr__(name, value)
            new_val = getattr(self, name, 0.0)
            delta = new_val - old_val
            if abs(delta) > 1e-5:
                # If target entity is taking damage, queue Attack instead of ModifyStat
                if (
                    self._entity_id != self._world_adapter.blackboard.entity_id
                    and name == "health"
                    and delta < 0.0
                ):
                    self._world_adapter.command_queue.push(
                        PyCommand(
                            PyCommandType.ATTACK,
                            self._world_adapter.blackboard.entity_id,
                            {"target_id": str(self._entity_id)},
                        )
                    )
                else:
                    self._world_adapter.command_queue.push(
                        PyCommand(
                            PyCommandType.MODIFY_STAT,
                            self._entity_id,
                            {"stat_name": name, "amount": str(delta)},
                        )
                    )
        else:
            super().__setattr__(name, value)


class FfiEmotionalState(EmotionalState):
    """FFI proxy for EmotionalState to intercept mutations and queue commands."""

    def __init__(self, world_adapter: Any, entity_id: int, *args: Any, **kwargs: Any) -> None:
        object.__setattr__(self, "_initialized", False)
        super().__init__(*args, **kwargs)
        object.__setattr__(self, "_world_adapter", world_adapter)
        object.__setattr__(self, "_entity_id", entity_id)
        object.__setattr__(self, "_initialized", True)

    def __setattr__(self, name: str, value: Any) -> None:
        if getattr(self, "_initialized", False) and name not in (
            "_initialized",
            "_world_adapter",
            "_entity_id",
        ):
            old_val = getattr(self, name, 0.0)
            super().__setattr__(name, value)
            new_val = getattr(self, name, 0.0)
            delta = new_val - old_val
            if abs(delta) > 1e-5:
                self._world_adapter.command_queue.push(
                    PyCommand(
                        PyCommandType.MODIFY_STAT,
                        self._entity_id,
                        {"stat_name": name, "amount": str(delta)},
                    )
                )
        else:
            super().__setattr__(name, value)


try:
    import py_trees
except ImportError:
    pass

try:
    import yukkuri_rust # type: ignore
    RustCommand = yukkuri_rust.Command
    RustCommandType = yukkuri_rust.CommandType
except ImportError:
    class MockRustCommandType:
        """Mock version of Rust CommandType enum."""
        MoveTo = "MoveTo"
        Flee = "Flee"
        Speak = "Speak"
        PlayAnimation = "PlayAnimation"
        Attack = "Attack"
        Interact = "Interact"
        ModifyStat = "ModifyStat"

    class MockRustCommand:
        """Mock version of Rust Command struct."""
        def __init__(
            self,
            cmd_type: Any,
            entity_id: int,
            payload: dict[str, str]
        ) -> None:
            self.cmd_type = cmd_type
            self.entity_id = entity_id
            self.payload = payload

    RustCommand = MockRustCommand
    RustCommandType = MockRustCommandType


MAP_COMMAND_TYPE: dict[PyCommandType, Any] = {
    PyCommandType.MOVE_TO: RustCommandType.MoveTo,
    PyCommandType.FLEE: RustCommandType.Flee,
    PyCommandType.SPEAK: RustCommandType.Speak,
    PyCommandType.PLAY_ANIMATION: RustCommandType.PlayAnimation,
    PyCommandType.ATTACK: RustCommandType.Attack,
    PyCommandType.INTERACT: RustCommandType.Interact,
    PyCommandType.MODIFY_STAT: RustCommandType.ModifyStat,
}

_ai_states: dict[int, AIState] = {}
_behavior_trees: dict[int, Any] = {}
_world_adapters: dict[int, "BevyWorldAdapter"] = {}


class MockGrid:
    """Mock navigation grid."""

    def __init__(self, world_adapter: "BevyWorldAdapter") -> None:
        """Initializes MockGrid."""
        self.world_adapter = world_adapter

    @property
    def width(self) -> int:
        return self.world_adapter.blackboard.grid_width

    @property
    def height(self) -> int:
        return self.world_adapter.blackboard.grid_height

    def is_walkable(self, gx: int, gy: int, capability: int) -> bool:
        """Mock is_walkable query delegating to Rust blackboard.

        Args:
            gx: Grid X.
            gy: Grid Y.
            capability: Traversal capability mask.

        Returns:
            Boolean indicating walkability.
        """
        return self.world_adapter.blackboard.is_walkable(gx, gy, capability)


class MockNavigationService:
    """Mocked NavigationService for behavior trees."""

    def __init__(self, world_adapter: "BevyWorldAdapter") -> None:
        """Initializes MockNavigationService.

        Args:
            world_adapter: The world adapter instance.
        """
        self.world_adapter = world_adapter
        self.grid_step_size: int = 25
        self.grid: MockGrid = MockGrid(world_adapter)

    def request_path(
        self,
        entity_id: int,
        start: tuple[float, float],
        end: tuple[float, float],
        capabilities: int = 0,
        priority: int = 2,
        timestamp: float | None = None,
    ) -> None:
        """Mock request path.

        Immediately sets the entity's path to [end] and sets path_requesting
        to False.

        Args:
            entity_id: The ID of the navigating entity.
            start: Start coordinate tuple.
            end: End coordinate tuple.
            capabilities: Travel capability bitmask.
            priority: Priority flag.
            timestamp: Optional request timestamp.
        """
        ai_state = self.world_adapter.try_get_component(entity_id, AIState)
        if ai_state:
            ai_state.path = [end]
            if ai_state.state_data is None:
                ai_state.state_data = {}
            ai_state.state_data["path_requesting"] = False


class MockGameService:
    """Mocked GameService for behavior trees."""

    def __init__(self, world_adapter: "BevyWorldAdapter") -> None:
        """Initializes MockGameService.

        Args:
            world_adapter: The world adapter instance.
        """
        self.world_adapter = world_adapter

    def find_best_item(
        self,
        position: tuple[float, float],
        criteria: str,
        exclude_ids: set[int] | None = None,
        searcher_id: int | None = None,
    ) -> int:
        """Mock find best item.

        Searches blackboard.visible_targets and returns closest item ID.

        Args:
            position: Search origin position.
            criteria: Stat criteria to search for.
            exclude_ids: Set of entity IDs to ignore.
            searcher_id: ID of searching entity.

        Returns:
            The ID of the closest matching item, or -1 if none found.
        """
        if exclude_ids is None:
            exclude_ids = set()

        closest_id = -1
        min_dist = float("inf")

        for target in self.world_adapter.blackboard.visible_targets:
            if target.entity_id in exclude_ids:
                continue

            tags_lower = {tag.lower() for tag in target.tags}
            is_match = False

            if criteria == "nutrition" and (
                "food" in tags_lower or "nutrition" in tags_lower
            ):
                is_match = True
            elif criteria == "fun" and (
                "toy" in tags_lower or "fun" in tags_lower or "item" in tags_lower
            ):
                is_match = True
            elif criteria == "comfort" and (
                "bed" in tags_lower or "comfort" in tags_lower or "item" in tags_lower
            ):
                is_match = True
            elif not criteria:
                is_match = any(
                    x in tags_lower for x in ["food", "toy", "bed", "item"]
                )

            if not target.tags:
                if not (target.is_prey or target.is_threat or target.is_family):
                    is_match = True

            if is_match or not criteria:
                if target.distance < min_dist:
                    min_dist = target.distance
                    closest_id = target.entity_id

        return closest_id


class MockTimeService:
    """Mocked TimeService for behavior trees."""

    def __init__(self) -> None:
        """Initializes MockTimeService."""
        self.time_elapsed: float = 0.0
        self.game_speed: float = 1.0
        self.scale: float = 60.0
        self.game_delta_multiplier: float = 60.0
        self.time_of_day: float = 12.0
        self.hour_of_day: float = 12.0
        self.is_night: bool = False
        self.day: int = 1


class MockSpatialService:
    """Mocked ISpatialService for behavior trees."""

    def __init__(self, world_adapter: "BevyWorldAdapter") -> None:
        """Initializes MockSpatialService.

        Args:
            world_adapter: The world adapter instance.
        """
        self.world_adapter = world_adapter

    def get_nearest_entity(
        self,
        world: Any,
        x: float,
        y: float,
        component_filter: Any,
        max_radius: float = 2000.0,
        exclude_ids: set[int] | None = None,
    ) -> int:
        """Mock get nearest entity.

        Searches blackboard.visible_targets for closest entity matching filter.

        Args:
            world: The ECS world (unused).
            x: Origin X position.
            y: Origin Y position.
            component_filter: The class type to filter by.
            max_radius: Max search radius.
            exclude_ids: Set of entity IDs to ignore.

        Returns:
            The ID of the nearest entity, or -1 if none found.
        """
        if exclude_ids is None:
            exclude_ids = set()

        closest_id = -1
        min_dist = float("inf")

        for target in self.world_adapter.blackboard.visible_targets:
            if target.entity_id in exclude_ids:
                continue
            if target.distance > max_radius:
                continue

            comp = self.world_adapter.try_get_component(
                target.entity_id, component_filter
            )
            if comp is not None:
                if target.distance < min_dist:
                    min_dist = target.distance
                    closest_id = target.entity_id

        return closest_id


class MockUtilityAIEngine:
    """Mocked UtilityAIEngine for behavior trees."""

    def select_action(
        self,
        context,
        personality=None,
        trait_service=None,
        exclude_actions=None,
    ):
        return "Wander"


class MockTraitService:
    """Mocked TraitService for behavior trees that actually loads traits.toml."""

    def __init__(self):
        import os
        import msgspec
        from ...engine.data_models import TraitDefinition

        self.traits = {}
        traits_path = os.path.join("data", "traits", "traits.toml")
        if os.path.exists(traits_path):
            with open(traits_path, "rb") as f:
                content = f.read()
                try:
                    raw = msgspec.toml.decode(content)
                    if "traits" in raw:
                        for k, v in raw["traits"].items():
                            self.traits[k] = msgspec.convert(v, TraitDefinition)
                except Exception as e:
                    print(f"Failed to parse traits.toml in MockTraitService: {e}")

    def get_trait(self, trait_id: str) -> Any:
        return self.traits.get(trait_id)

    def calculate_overrides(self, traits: set[str]) -> dict[str, Any]:
        overrides = {}
        for trait_id in sorted(traits):
            trait_data = self.get_trait(trait_id)
            if trait_data and trait_data.ai_modifiers:
                for cons_name, mod in trait_data.ai_modifiers.items():
                    overrides[cons_name] = mod
        return overrides



class MockServiceLocator:
    """Mocked service locator returned by self.world.services."""

    def __init__(self, world_adapter: "BevyWorldAdapter") -> None:
        """Initializes MockServiceLocator.

        Args:
            world_adapter: The world adapter instance.
        """
        self.world_adapter = world_adapter

    def try_get(self, service_class: Any) -> Any:
        """Try to retrieve a registered service by class.

        Args:
            service_class: The class of the service to retrieve.

        Returns:
            The service instance if mocked, or None.
        """
        class_name = (
            service_class.__name__
            if hasattr(service_class, "__name__")
            else str(service_class)
        )
        if "NavigationService" in class_name:
            return MockNavigationService(self.world_adapter)
        if "GameService" in class_name:
            return MockGameService(self.world_adapter)
        if "TimeService" in class_name:
            return MockTimeService()
        if "ISpatialService" in class_name:
            return MockSpatialService(self.world_adapter)
        if "CommandQueue" in class_name:
            return self.world_adapter.command_queue
        if "UtilityAIEngine" in class_name:
            return MockUtilityAIEngine()
        if "TraitService" in class_name:
            return MockTraitService()
        return None


class MockCommandBuffer:
    """Mock command buffer to prevent AttributeError when behaviors access world.commands."""

    def __init__(self, world_adapter: "BevyWorldAdapter") -> None:
        self.world_adapter = world_adapter

    def add_component(self, entity_id: int, component: Any) -> None:
        """Mock add_component.

        Args:
            entity_id: The ID of the entity.
            component: The component instance to add.
        """
        class_name = component.__class__.__name__
        if "InteractionRequest" in class_name:
            target_id = getattr(component, "target_id", None)
            action = getattr(component, "action", None)
            consume = getattr(component, "consume", False)
            if target_id is not None and action is not None:
                self.world_adapter.command_queue.push(
                    PyCommand(
                        PyCommandType.INTERACT,
                        entity_id,
                        {
                            "target_id": str(target_id),
                            "action": str(action),
                            "consume": str(consume),
                        },
                    )
                )

    def remove_component(self, entity_id: int, component_type: type[Any]) -> None:
        """Mock remove_component.

        Args:
            entity_id: The ID of the entity.
            component_type: The component class to remove.
        """
        pass

    def destroy_entity(self, entity_id: int) -> None:
        """Mock destroy_entity.

        Args:
            entity_id: The ID of the entity to destroy.
        """
        pass

    def create_entity(self, *components: Any) -> int:
        """Mock create_entity.

        Args:
            *components: The component instances for the new entity.

        Returns:
            The ID of the newly created entity (always 0).
        """
        return 0


class BevyWorldAdapter:
    """Adapter mocking the esper World interface for behavior tree queries."""

    def __init__(self, blackboard: Any) -> None:
        """Initializes BevyWorldAdapter with Bevy blackboard.

        Args:
            blackboard: The Rust blackboard struct from PyO3.
        """
        self.blackboard = blackboard
        self.time: float = 0.0
        self.targets: dict[int, Any] = {
            t.entity_id: t for t in blackboard.visible_targets
        }
        self.command_queue: PyCommandQueue = PyCommandQueue()
        self.services: MockServiceLocator = MockServiceLocator(self)
        self.commands: MockCommandBuffer = MockCommandBuffer(self)


    def update_blackboard(self, blackboard: Any) -> None:
        """Updates the internal blackboard reference and state in-place.

        Args:
            blackboard: The new Rust blackboard struct from PyO3.
        """
        self.blackboard = blackboard
        self.time = blackboard.stats.get("game_time", 0.0)
        self.targets = {t.entity_id: t for t in blackboard.visible_targets}
        self.command_queue.clear()

    def get_all_entities(self) -> list[int]:
        """Returns empty list since BevyWorldAdapter uses Bevy queries and spatial service."""
        return []

    def get_components(self, component_type: Any) -> dict[int, Any]:
        """Returns empty dict since BevyWorldAdapter uses Bevy queries and spatial service."""
        return {}

    def has_component(self, entity_id: int, component_type: Any) -> bool:
        """Checks if the entity has the requested component type.

        Args:
            entity_id: The ID of the entity.
            component_type: The component class.

        Returns:
            True if the component exists, False otherwise.
        """
        return self.try_get_component(entity_id, component_type) is not None

    def get_components_tuple(
        self, *component_types: Any
    ) -> list[tuple[int, tuple[Any, ...]]]:
        """Gets tuples of components for all entities in the adapter.

        Args:
            *component_types: The component types to query.

        Returns:
            A list of tuples of (entity_id, component_tuple).
        """
        results = []
        t_id = self.blackboard.entity_id
        comps = []
        for c_type in component_types:
            comp = self.try_get_component(t_id, c_type)
            if comp is not None:
                comps.append(comp)
            else:
                break
        if len(comps) == len(component_types):
            results.append((t_id, tuple(comps)))

        for target in self.blackboard.visible_targets:
            uid = target.entity_id
            comps = []
            for c_type in component_types:
                comp = self.try_get_component(uid, c_type)
                if comp is not None:
                    comps.append(comp)
                else:
                    break
            if len(comps) == len(component_types):
                results.append((uid, tuple(comps)))

        return results

    def try_get_component(self, entity_id: int, component_type: Any) -> Any:
        """Attempts to retrieve the component for the entity.

        Args:
            entity_id: The ID of the entity.
            component_type: The component class.

        Returns:
            The component instance, or None if not found.
        """
        if entity_id == self.blackboard.entity_id:
            if component_type == Transform:
                return Transform(x=self.blackboard.x, y=self.blackboard.y)

            if component_type == Needs:
                return FfiNeeds(
                    self,
                    entity_id,
                    max_health=self.blackboard.stats.get("max_health", 100.0),
                    health=self.blackboard.stats.get("health", 100.0),
                    hunger=self.blackboard.stats.get("hunger", 0.0),
                    social=self.blackboard.stats.get("social", 50.0),
                    energy=self.blackboard.stats.get("energy", 100.0),
                    cleanliness=self.blackboard.stats.get("cleanliness", 100.0),
                    bladder=self.blackboard.stats.get("bladder", 0.0),
                    easiness=self.blackboard.stats.get("easiness", 50.0),
                )

            if component_type == YukkuriStats:
                type_id = getattr(self.blackboard, "type_id", "reimu")
                growth_stage = getattr(self.blackboard, "growth_stage", "Adult")
                name = self.blackboard.stats.get("name", type_id)
                return YukkuriStats(
                    name=name, type_id=type_id, growth_stage=growth_stage
                )

            if component_type == AIState:
                if entity_id not in _ai_states:
                    _ai_states[entity_id] = AIState(
                        current_action=self.blackboard.current_action,
                        state_data={},
                        manual_override=False,
                    )
                else:
                    _ai_states[entity_id].current_action = (
                        self.blackboard.current_action
                    )
                    # Let utility AI run
                return _ai_states[entity_id]

            if component_type == PyBlackboard:
                vis_dict = {}
                for target in self.blackboard.visible_targets:
                    if target.is_threat:
                        relation = "Enemy"
                    elif target.is_family:
                        relation = "Family"
                    elif target.is_prey:
                        relation = "Prey"
                    elif target.affinity > 50.0:
                        relation = "Friend"
                    elif target.affinity < -50.0:
                        relation = "Enemy"
                    else:
                        relation = "Neutral"

                    vis_dict[target.entity_id] = PyTargetInfo(
                        entity_id=target.entity_id,
                        position=(target.x, target.y),
                        distance=target.distance,
                        relation=relation,
                        timestamp=0.0,
                        detected_at=0.0,
                    )

                stm_dict = {}
                if self.blackboard.short_term_memory:
                    for k, v in self.blackboard.short_term_memory.items():
                        stm_dict[k] = PyLastKnownPosition(
                            position=(v[0], v[1]),
                            timestamp=v[2],
                        )

                nearby_friends = sum(
                    1 for t in vis_dict.values() if t.relation == "Friend"
                )
                nearby_enemies = sum(
                    1 for t in vis_dict.values() if t.relation == "Enemy"
                )
                nearby_prey = sum(
                    1 for t in vis_dict.values() if t.relation == "Prey"
                )

                closest_threat_id = None
                min_threat_dist = float("inf")
                for t in self.blackboard.visible_targets:
                    if t.is_threat or t.affinity < -50.0:
                        if t.distance < min_threat_dist:
                            min_threat_dist = t.distance
                            closest_threat_id = t.entity_id

                closest_food_id = None
                min_food_dist = float("inf")
                for t in self.blackboard.visible_targets:
                    tags_lower = {tag.lower() for tag in t.tags}
                    if "food" in tags_lower or "nutrition" in tags_lower:
                        if t.distance < min_food_dist:
                            min_food_dist = t.distance
                            closest_food_id = t.entity_id

                return PyBlackboard(
                    visible_targets=vis_dict,
                    short_term_memory=stm_dict,
                    nearby_friends=nearby_friends,
                    nearby_enemies=nearby_enemies,
                    nearby_prey=nearby_prey,
                    closest_threat_id=closest_threat_id,
                    closest_food_id=closest_food_id,
                )

            if component_type == MovementController:
                return MovementController(
                    target_velocity=pymunk.vec2d.Vec2d(0, 0),
                    current_velocity=pymunk.vec2d.Vec2d(0, 0),
                )

            if component_type == Flight:
                stamina = self.blackboard.stats.get("stamina", 100.0)
                return Flight(
                    altitude=getattr(self.blackboard, "altitude", 0.0),
                    max_altitude=60.0,
                    vertical_speed=20.0,
                    stamina=stamina,
                    max_stamina=100.0,
                    fly_cost=5.0,
                    hover_cost=1.0,
                    recovery_rate=10.0,
                    state=FlightState(getattr(self.blackboard, "flight_state", 0)),
                )

            if component_type == EmotionalState:
                return FfiEmotionalState(
                    self,
                    entity_id,
                    happiness=self.blackboard.stats.get("happiness", 0.0),
                    stress=self.blackboard.stats.get("stress", 0.0),
                )

            if component_type == Mount:
                parent_id = self.blackboard.parent_id if self.blackboard.parent_id is not None else -1
                return Mount(
                    parent_id=parent_id,
                    children_ids=list(self.blackboard.children_ids),
                    structure_dirty=False
                )

            if component_type == InventoryComponent:
                items = [ItemStack(item_type_id=x[0], quantity=x[1]) for x in self.blackboard.inventory]
                return InventoryComponent(
                    capacity=20,
                    items=items
                )

            if component_type == Personality:
                kindness = int(self.blackboard.stats.get("kindness", 0.0))
                energy = int(self.blackboard.stats.get("energy_personality", 0.0))
                bravery = int(self.blackboard.stats.get("bravery", 0.0))
                greed = int(self.blackboard.stats.get("greed", 0.0))
                traits = set(getattr(self.blackboard, "traits", []))
                return Personality(
                    axis=PersonalityAxis(
                        kindness=kindness,
                        energy=energy,
                        bravery=bravery,
                        greed=greed,
                    ),
                    traits=traits,
                )

            if component_type == Skills:
                states = {}
                skills = getattr(self.blackboard, "skills", None)
                if skills:
                    for skill_id, lvl in skills.items():
                        states[skill_id] = SkillState(level=lvl)
                return Skills(states=states)


        for target in self.blackboard.visible_targets:
            if target.entity_id == entity_id:
                if component_type == Personality:
                    return Personality()
                if component_type == Transform:
                    return Transform(x=target.x, y=target.y)
                if component_type == YukkuriStats:
                    is_yukkuri = target.is_prey or target.is_threat or target.is_family or any(
                        y in target.type_id.lower() for y in ["reimu", "marisa", "yukkuri"]
                    )
                    if is_yukkuri:
                        return YukkuriStats(
                            name=target.type_id,
                            type_id=target.type_id,
                            growth_stage=target.growth_stage,
                        )
                    return None
                if component_type == Needs:
                    is_yukkuri = target.is_prey or target.is_threat or target.is_family or any(
                        y in target.type_id.lower() for y in ["reimu", "marisa", "yukkuri"]
                    )
                    if is_yukkuri:
                        return FfiNeeds(self, entity_id, health=100.0, hunger=0.0, social=50.0, energy=100.0)
                    return None
                if component_type == ItemStats:
                    tags_lower = {tag.lower() for tag in target.tags}
                    is_item = any(
                        x in tags_lower
                        for x in ["food", "item", "toy", "bed", "nutrition", "fun", "comfort"]
                    )
                    if not target.tags and not (target.is_prey or target.is_threat or target.is_family):
                        is_item = True
                    if is_item:
                        return ItemStats(
                            name=target.type_id,
                            type_id=target.type_id,
                            cost=0,
                            nutrition=50.0,
                            fun=50.0,
                            comfort=50.0,
                        )
                    return None
                if component_type == Predator:
                    if target.is_threat or "predator" in {tag.lower() for tag in target.tags}:
                        return Predator(
                            prey_tags=set(["Yukkuri", "reimu", "marisa"]),
                            prey_sense_radius=300.0,
                            hunger_threshold=60.0,
                            aggression=1.0,
                            dps=20.0,
                        )
                    return None

        return None


def tick_entity_with_blackboard(blackboard: Any) -> list[Any]:
    """FFI entrypoint to tick a single entity's behavior tree using a blackboard.

    Args:
        blackboard: The Rust Blackboard class containing snapshot data.

    Returns:
        A list of PyO3 Command objects generated during the tick.
    """
    entity_id = blackboard.entity_id

    if entity_id not in _behavior_trees:
        world_adapter = BevyWorldAdapter(blackboard)
        _world_adapters[entity_id] = world_adapter
        root = create_yukkuri_behavior_tree(
            entity_id, world_adapter, width=3000, height=3000
        )
        tree = py_trees.trees.BehaviourTree(root)
        try:
            tree.setup(timeout=15)
        except ValueError as e:
            if "signal only works in main thread" not in str(e):
                raise
        _behavior_trees[entity_id] = tree
    else:
        world_adapter = _world_adapters[entity_id]
        world_adapter.update_blackboard(blackboard)
        for node in _behavior_trees[entity_id].root.iterate():
            if hasattr(node, "world"):
                node.world = world_adapter

    dt = blackboard.stats.get("dt", 0.1)
    py_trees.blackboard.Blackboard().set("dt", dt)

    _behavior_trees[entity_id].tick()

    commands = world_adapter.command_queue.pop_all()
    rust_commands = []
    for cmd in commands:
        rust_cmd_type = MAP_COMMAND_TYPE.get(cmd.type)
        if rust_cmd_type is not None:
            payload_str = {str(k): str(v) for k, v in cmd.payload.items()}
            rust_commands.append(
                RustCommand(rust_cmd_type, cmd.entity_id, payload_str)
            )

    return rust_commands


def serialize_ai_state(entity_id: int) -> bytes:
    """Serializes the AIState of the given entity to MessagePack bytes.

    Args:
        entity_id: The ID of the entity.

    Returns:
        MessagePack bytes containing the AIState variables.
    """
    state = _ai_states.get(entity_id)
    if state is None:
        return b""

    # Convert sets of EntityID to lists of ints for serialization
    failed_targets = [int(x) for x in state.failed_targets]
    visible_entities = [int(x) for x in state.visible_entities]

    data = {
        "current_action": state.current_action,
        "current_target_id": int(state.current_target_id),
        "path": state.path,
        "action_progress": state.action_progress,
        "state_data": state.state_data,
        "failed_targets": failed_targets,
        "visible_entities": visible_entities,
        "manual_override": state.manual_override,
        "is_inspected": state.is_inspected,
        "last_utility_breakdown": state.last_utility_breakdown,
        "action_cooldowns": state.action_cooldowns,
    }
    import msgspec
    return msgspec.msgpack.encode(data)


def deserialize_ai_state(
    entity_id: int, blob: bytes, id_map: dict[int, int]
) -> None:
    """Deserializes and remaps the AIState of an entity from MsgPack bytes.

    Args:
        entity_id: The new entity ID.
        blob: MessagePack bytes.
        id_map: Mapping from old entity ID to new entity ID.
    """
    if not blob:
        return
    import msgspec
    from ..components.social import AIState
    from ...engine.types import EntityID

    data = msgspec.msgpack.decode(blob)

    # Remap EntityIDs
    old_target_id = data.get("current_target_id", -1)
    new_target_id = id_map.get(old_target_id, -1) if old_target_id != -1 else -1

    failed_targets = set()
    for x in data.get("failed_targets", []):
        new_val = id_map.get(x, x)
        failed_targets.add(EntityID(new_val))

    visible_entities = set()
    for x in data.get("visible_entities", []):
        new_val = id_map.get(x, x)
        visible_entities.add(EntityID(new_val))

    # Also remap any entity IDs inside state_data if present
    state_data = data.get("state_data")
    if state_data and isinstance(state_data, dict):
        if "target_id" in state_data:
            old_t = state_data["target_id"]
            if isinstance(old_t, int):
                state_data["target_id"] = id_map.get(old_t, old_t)

    state = AIState(
        current_action=data.get("current_action", "Idle"),
        current_target_id=EntityID(new_target_id),
        path=data.get("path"),
        action_progress=data.get("action_progress", 0.0),
        state_data=state_data,
        failed_targets=failed_targets,
        visible_entities=visible_entities,
        manual_override=data.get("manual_override", False),
        is_inspected=data.get("is_inspected", False),
        last_utility_breakdown=data.get("last_utility_breakdown"),
        action_cooldowns=data.get("action_cooldowns", {}),
    )
    _ai_states[entity_id] = state


def cleanup_entity_cache(entity_id: int) -> None:
    """Removes cached behavior tree and world adapter for despawned entities."""
    _behavior_trees.pop(entity_id, None)
    _world_adapters.pop(entity_id, None)
    _ai_states.pop(entity_id, None)

