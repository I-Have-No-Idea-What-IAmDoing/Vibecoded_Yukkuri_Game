import math
from typing import TYPE_CHECKING, Any, cast, Optional

from py_trees.common import Status

from yukkuri_game.engine.types import EntityID

from ....components import (
    LightSource,
    Transform,
)
from ....services import GameService
from ....yukkuri_components import (
    AIState,
    Blackboard,
    Flight,
    ItemStats,
    Predator,
    YukkuriStats,
)
from ...base_action import Action
from ...navigation_constants import TraversalCapability
from ...navigation_service import NavigationService

if TYPE_CHECKING:
    from yukkuri_game.engine.ecs import World
    from yukkuri_game.game.systems.sector_system import SectorMap


class FindItem(Action):
    """
    Action to find an item based on criteria.

    Attributes:
        stat_criteria (str): The item stat to look for (e.g., "nutrition", "fun").
    """

    def __init__(self, name: str, entity_id: int, world: "World", stat_criteria: str):
        """
        Initializes the FindItem action.

        Args:
            name (str): The name of the node.
            entity_id (int): The entity ID.
            world (World): The ECS World.
            stat_criteria (str): The item stat to optimize for.
        """
        super().__init__(name, entity_id, world)
        self.stat_criteria = stat_criteria

    def update(self) -> Status:
        super().update()
        if self.world is None or self.entity_id is None:
            return Status.FAILURE

        ai = self.world.get_component(self.entity_id, AIState)
        trans = self.world.get_component(self.entity_id, Transform)

        if ai is None or trans is None:
            return Status.FAILURE

        if ai.manual_override and ai.current_target_id != -1:
            return Status.SUCCESS

        game_service = self.world.services.try_get(GameService)
        best_item = -1

        if game_service:
            best_item = game_service.find_best_item(
                (trans.x, trans.y),
                self.stat_criteria,
                exclude_ids={int(x) for x in ai.failed_targets},
                searcher_id=self.entity_id,
            )

        if best_item != -1:
            if ai.current_target_id != best_item:
                ai.current_target_id = cast(EntityID, best_item)
                ai.path = None

                # Anticipatory Caching
                nav_service = self.world.services.try_get(NavigationService)
                target_trans = self.world.get_component(best_item, Transform)
                if nav_service and target_trans:
                    capabilities = TraversalCapability.WALK
                    flight_comp = self.world.try_get_component(self.entity_id, Flight)
                    if flight_comp and flight_comp.stamina > 20:
                        capabilities |= TraversalCapability.FLY

                    nav_service.request_path(
                        self.entity_id,
                        (trans.x, trans.y),
                        (target_trans.x, target_trans.y),
                        capabilities=capabilities,
                        priority=0,
                    )
                    if ai.state_data is None:
                        ai.state_data = {}
                    ai.state_data["path_requesting"] = True
                    if "path_failed" in ai.state_data:
                        del ai.state_data["path_failed"]

            return Status.SUCCESS

        if ai.failed_targets:
            ai.failed_targets.clear()

        return Status.FAILURE


class FindLightSource(Action):
    """
    Action to find the nearest light source.
    """

    def __init__(self, name: str, entity_id: int, world: "World"):
        """
        Initializes the FindLightSource action.

        Args:
            name (str): The name of the node.
            entity_id (int): The entity ID.
            world (World): The ECS World.
        """
        super().__init__(name, entity_id, world)

    def update(self) -> Status:
        super().update()
        if not self.world or not self.entity_id:
            return Status.FAILURE

        ai = self.world.get_component(self.entity_id, AIState)
        trans = self.world.get_component(self.entity_id, Transform)

        if not ai or not trans:
            return Status.FAILURE

        if ai.manual_override and ai.current_target_id != -1:
            return Status.SUCCESS

        best_dist = float("inf")
        best_light = -1

        for ent, (l_trans, light) in self.world.get_components_tuple(
            Transform, LightSource
        ):
            if ent == self.entity_id:
                continue

            dist = math.hypot(l_trans.x - trans.x, l_trans.y - trans.y)
            if dist < best_dist:
                best_dist = dist
                best_light = ent

        if best_light != -1:
            if ai.current_target_id != best_light:
                ai.current_target_id = cast(EntityID, best_light)
                ai.path = None
            return Status.SUCCESS

        return Status.FAILURE


class FindPrey(Action):
    """
    Finds a target entity that matches the predator's prey tags.
    Optimized to use SectorMap for spatial queries.
    """

    def __init__(
        self,
        name: str = "Find Prey",
        entity_id: int | None = None,
        world: "World | None" = None,
        blackboard: Any | None = None,
    ):
        """
        Initializes the FindPrey action.

        Args:
            name (str): The name of the node.
            entity_id (int | None): The entity ID.
            world (World | None): The ECS World.
            blackboard (Any | None): The blackboard.
        """
        super().__init__(name, entity_id, world, blackboard)
        self.sector_map: Optional["SectorMap"] = None

    def update(self) -> Status:
        super().update()
        if self.world is None or self.entity_id is None:
            return Status.FAILURE

        ai = self.world.get_component(self.entity_id, AIState)
        predator = self.world.get_component(self.entity_id, Predator)
        trans = self.world.get_component(self.entity_id, Transform)

        if ai is None or predator is None or trans is None:
            return Status.FAILURE

        if ai.manual_override and ai.current_target_id != -1:
            return Status.SUCCESS

        # Lazy load SectorMap
        if self.sector_map is None:
            from ....systems.sector_system import SectorMap

            self.sector_map = self.world.services.try_get(SectorMap)

        candidates: list[tuple[int, float]] = []

        # Use efficient spatial query if available
        potential_targets = []
        if self.sector_map:
            potential_targets = self.sector_map.get_entities_in_radius(
                trans.x, trans.y, predator.prey_sense_radius
            )
        else:
            # Fallback to expensive full scan
            potential_targets = self.world.get_all_entities()

        # Filter candidates
        for ent in potential_targets:
            if ent == self.entity_id:
                continue

            # We need to manually check distance if we used SectorMap (it returns a superset)
            # Fetch components safely
            target_trans = self.world.try_get_component(ent, Transform)
            if not target_trans:
                continue

            # Distance check
            dist = math.hypot(target_trans.x - trans.x, target_trans.y - trans.y)
            if dist > predator.prey_sense_radius:
                continue

            # Type/Tag check
            is_prey = False

            # Check ItemStats
            i_stats = self.world.try_get_component(ent, ItemStats)
            if i_stats:
                if i_stats.type_id in predator.prey_tags:
                    is_prey = True
                elif "Food" in predator.prey_tags and i_stats.type_id in (
                    "beanpaste",
                    "food",
                    "cookie",
                ):
                    is_prey = True
                elif (
                    "BeanPaste" in predator.prey_tags and i_stats.type_id == "beanpaste"
                ):
                    is_prey = True

            # Check YukkuriStats
            if not is_prey:
                y_stats = self.world.try_get_component(ent, YukkuriStats)
                if y_stats:
                    if y_stats.type_id in predator.prey_tags:
                        is_prey = True
                    if "Yukkuri" in predator.prey_tags:
                        is_prey = True

            if is_prey:
                candidates.append((ent, dist))

        if not candidates:
            return Status.FAILURE

        candidates.sort(key=lambda x: x[1])
        best_target = candidates[0][0]

        if ai.current_target_id != best_target:
            ai.current_target_id = cast(EntityID, best_target)
            ai.path = None

        return Status.SUCCESS


class FindThreat(Action):
    """
    Finds the closest threat from Blackboard.
    """

    def __init__(
        self,
        name: str = "Find Threat",
        entity_id: int | None = None,
        world: "World | None" = None,
        blackboard: Any | None = None,
    ):
        """
        Initializes the FindThreat action.

        Args:
            name (str): The name of the node.
            entity_id (int | None): The entity ID.
            world (World | None): The ECS World.
            blackboard (Any | None): The blackboard.
        """
        super().__init__(name, entity_id, world, blackboard)

    def update(self) -> Status:
        super().update()
        if not self.world or self.entity_id is None:
            return Status.FAILURE

        ai = self.world.get_component(self.entity_id, AIState)
        blackboard_comp = self.world.try_get_component(self.entity_id, Blackboard)

        if not ai or not blackboard_comp:
            return Status.FAILURE

        if ai.manual_override and ai.current_target_id != -1:
            return Status.SUCCESS

        threat_id = blackboard_comp.closest_threat_id
        if threat_id is not None and threat_id != -1:
            ai.current_target_id = cast(EntityID, threat_id)
            return Status.SUCCESS

        return Status.FAILURE


class FindSocialTarget(Action):
    """
    Finds a target Yukkuri for social interaction based on criteria.

    Attributes:
        criteria (str): Criteria for selecting a target (e.g., "friend", "enemy", "any").
    """

    def __init__(self, name: str, entity_id: int, world: "World", criteria: str):
        """
        Initializes the FindSocialTarget action.

        Args:
            name (str): The name of the node.
            entity_id (int): The entity ID.
            world (World): The ECS World.
            criteria (str): Matching criteria ("friend", "enemy", "any").
        """
        super().__init__(name, entity_id, world)
        self.criteria = criteria

    def update(self) -> Status:
        super().update()
        if not self.world or not self.entity_id:
            return Status.FAILURE

        ai = self.world.get_component(self.entity_id, AIState)
        my_stats = self.world.get_component(self.entity_id, YukkuriStats)
        trans = self.world.get_component(self.entity_id, Transform)

        if ai is None or my_stats is None or trans is None:
            return Status.FAILURE

        if ai.manual_override and ai.current_target_id != -1:
            return Status.SUCCESS

        nearby_yukkuris = self.world.get_entities_with(YukkuriStats, Transform)

        best_target = -1
        min_dist = float("inf")

        for uid in nearby_yukkuris:
            if uid == self.entity_id:
                continue

            if uid in ai.failed_targets:
                continue

            u_stats = self.world.get_component(uid, YukkuriStats)
            u_trans = self.world.get_component(uid, Transform)

            if u_stats is None or u_trans is None:
                continue

            is_compatible = u_stats.type_id == my_stats.type_id

            match = False
            if self.criteria == "any":
                match = True
            elif self.criteria == "friend" and is_compatible:
                match = True
            elif self.criteria == "enemy" and not is_compatible:
                match = True

            if match:
                dist = math.hypot(u_trans.x - trans.x, u_trans.y - trans.y)
                if dist < min_dist:
                    min_dist = dist
                    best_target = uid

        if best_target != -1:
            if ai.current_target_id != best_target:
                ai.current_target_id = cast(EntityID, best_target)
                ai.path = None
            return Status.SUCCESS

        return Status.FAILURE


class PickFood(Action):
    """
    Selects the closest food from the blackboard.
    """

    def __init__(
        self,
        name: str = "Pick Food",
        entity_id: int | None = None,
        world: "World | None" = None,
        blackboard: Any | None = None,
    ):
        """
        Initializes the PickFood action.

        Args:
            name (str): The name of the node.
            entity_id (int | None): The entity ID.
            world (World | None): The ECS World.
            blackboard (Any | None): The blackboard.
        """
        super().__init__(name, entity_id, world, blackboard)

    def update(self) -> Status:
        super().update()
        if not self.world or self.entity_id is None:
            return Status.FAILURE
        ai = self.world.get_component(self.entity_id, AIState)
        if not ai:
            return Status.FAILURE

        if ai.manual_override and ai.current_target_id != -1:
            return Status.SUCCESS
        bb = self.world.try_get_component(self.entity_id, Blackboard)
        if bb and bb.closest_food_id:
            ai.current_target_id = cast(EntityID, bb.closest_food_id)
            return Status.SUCCESS
        return Status.FAILURE
