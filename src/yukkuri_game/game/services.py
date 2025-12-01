"""
Module defining core game services.
"""
import os
import json
from typing import Dict, Any, List, TYPE_CHECKING, Optional
from loguru import logger
from ..engine.ecs import World
from ..engine.audio import AudioManager
from .components import Transform
from .yukkuri_components import YukkuriStats, ItemStats, AIState, EmotionalState, Personality, GossipQueue
from ..engine.service_locator import ServiceLocator
from .prefabs.yukkuri import create_yukkuri
from .prefabs.item import create_item

class TimeService:
    """
    Service responsible for tracking game time.

    Attributes:
        _time_elapsed (float): The total elapsed game time in seconds.
    """
    def __init__(self, time_elapsed: float = 0.0) -> None:
        """Initializes the TimeService."""
        self._time_elapsed = time_elapsed

    @property
    def time_elapsed(self) -> float:
        return self._time_elapsed

    @time_elapsed.setter
    def time_elapsed(self, value: float) -> None:
        self._time_elapsed = value

    def add_time(self, dt: float) -> None:
        self._time_elapsed += dt

class EconomyService:
    """
    Service responsible for managing the player's economy.

    Attributes:
        _money (int): The current amount of money.
    """
    def __init__(self, initial_money: int = 1000):
        self._money = initial_money

    def get_money(self) -> int:
        return self._money

    def add_money(self, amount: int) -> None:
        if amount < 0:
            raise ValueError("Cannot add negative money.")
        self._money += amount

    def remove_money(self, amount: int) -> bool:
        if amount < 0:
             raise ValueError("Cannot remove negative money.")
        if self._money >= amount:
            self._money -= amount
            return True
        return False

    def set_money(self, amount: int) -> None:
        if amount < 0:
             self._money = 0
        else:
             self._money = amount

class InputService:
    """
    Service responsible for managing input state, specifically placement mode and selection.
    """
    def __init__(self) -> None:
        self._placing_mode = False
        self._place_type: str = ""
        self._place_cost: int = 0
        self._place_entity_type: str = "" # "yukkuri" or "item"
        self._cleaning_mode = False
        self.hovered_entity_id: int = -1
        self.hovered_entity_pos: tuple[int, int] = (0, 0)

        # New selection/drag state
        self.drag_start_pos: tuple[int, int] = (0, 0)
        self.drag_current_pos: tuple[int, int] = (0, 0)
        self.is_dragging: bool = False

    @property
    def is_placing(self) -> bool:
        return self._placing_mode

    @property
    def is_cleaning(self) -> bool:
        return self._cleaning_mode

    @property
    def place_type(self) -> str:
        return self._place_type

    @property
    def place_cost(self) -> int:
        return self._place_cost

    @property
    def place_entity_type(self) -> str:
        return self._place_entity_type

    def start_placement(self, type_id: str, cost: int, entity_type: str) -> None:
        self._placing_mode = True
        self._cleaning_mode = False
        self._place_type = type_id
        self._place_cost = cost
        self._place_entity_type = entity_type

    def cancel_placement(self) -> None:
        self._placing_mode = False
        self._place_type = ""
        self._place_cost = 0
        self._place_entity_type = ""

    def start_cleaning(self) -> None:
        self._cleaning_mode = True
        self._placing_mode = False

    def stop_cleaning(self) -> None:
        self._cleaning_mode = False

class GameService:
    """
    Service providing game-specific logic and utilities.
    """
    def __init__(self, world: World):
        self.world = world

    def find_best_item(self, position: tuple[float, float], stat_criteria: str = "nutrition", exclude_ids: set[int] | None = None) -> int:
        import math
        best_dist = float('inf')
        best_item = -1

        if exclude_ids is None:
            exclude_ids = set()

        from .components import Transform
        from .yukkuri_components import ItemStats

        items = self.world.get_entities_with(ItemStats, Transform)

        for item in items:
            if item in exclude_ids:
                continue

            istats = self.world.get_component(item, ItemStats)
            itrans = self.world.get_component(item, Transform)

            if istats and itrans and getattr(istats, stat_criteria, 0.0) > 0:
                d = math.hypot(itrans.x - position[0], itrans.y - position[1])
                if d < best_dist:
                    best_dist = d
                    best_item = item

        return best_item

    def interact_with_item(self, consumer_id: int, item_id: int, consume: bool = True) -> bool:
        from .components import Transform
        from .yukkuri_components import YukkuriStats, ItemStats, AIState, EmotionalState

        if not self.world.entity_exists(consumer_id) or not self.world.entity_exists(item_id):
            return False

        item_stats = self.world.get_component(item_id, ItemStats)
        yukkuri_stats = self.world.get_component(consumer_id, YukkuriStats)
        emotional = self.world.get_component(consumer_id, EmotionalState)

        if item_stats and yukkuri_stats:
            if item_stats.nutrition > 0:
                yukkuri_stats.hunger = max(0, yukkuri_stats.hunger - item_stats.nutrition)

            if item_stats.fun > 0 and emotional:
                emotional.happiness = min(100, emotional.happiness + item_stats.fun)

            if item_stats.comfort > 0:
                yukkuri_stats.energy = min(100, yukkuri_stats.energy + item_stats.comfort)

            audio = self.world.services.try_get(AudioManager)

            if consume:
                if audio:
                    audio.play_sound("eat")
                self.world.destroy_entity(item_id)
                if self.world.has_component(item_id, Transform):
                    self.world.remove_component(item_id, Transform)

                ai = self.world.get_component(consumer_id, AIState)
                if ai and ai.current_target_id == item_id:
                    ai.current_target_id = -1
            else:
                pass

            return True

        return False

    def interact_social(self, initiator_id: int, target_id: int, interaction_type: str) -> bool:
        if not self.world.entity_exists(initiator_id) or not self.world.entity_exists(target_id):
            return False

        init_stats = self.world.get_component(initiator_id, YukkuriStats)
        target_stats = self.world.get_component(target_id, YukkuriStats)
        init_emo = self.world.get_component(initiator_id, EmotionalState)
        target_emo = self.world.get_component(target_id, EmotionalState)

        if not init_stats or not target_stats:
            return False

        audio = self.world.services.try_get(AudioManager)

        if interaction_type == "Talk":
            if init_emo: init_emo.happiness = min(100.0, init_emo.happiness + 5.0)
            init_stats.social = min(100.0, init_stats.social + 15.0)
            if target_emo: target_emo.happiness = min(100.0, target_emo.happiness + 5.0)
            target_stats.social = min(100.0, target_stats.social + 15.0)

            init_gossip = self.world.get_component(initiator_id, GossipQueue)
            target_gossip = self.world.get_component(target_id, GossipQueue)

            if init_gossip and target_gossip:
                for packet in init_gossip.priority_queue[:3]:
                    target_gossip.add_packet(packet)
                for packet in target_gossip.priority_queue[:3]:
                    init_gossip.add_packet(packet)

            if audio:
                 if hasattr(audio, 'play_sound'):
                     audio.play_sound("talk")

        elif interaction_type == "Fight":
            damage = 5.0
            init_stats.health = max(0.0, init_stats.health - damage)
            if init_emo:
                init_emo.happiness = max(-100.0, init_emo.happiness - 10.0)
                init_emo.stress = min(100.0, init_emo.stress + 10.0)

            target_stats.health = max(0.0, target_stats.health - damage)
            if target_emo:
                target_emo.happiness = max(-100.0, target_emo.happiness - 10.0)
                target_emo.stress = min(100.0, target_emo.stress + 10.0)

            if audio:
                 if hasattr(audio, 'play_sound'):
                    audio.play_sound("hit")

        elif interaction_type == "Dance":
            if init_emo: init_emo.happiness = min(100.0, init_emo.happiness + 10.0)
            if target_emo: target_emo.happiness = min(100.0, target_emo.happiness + 10.0)
            init_stats.social = min(100.0, init_stats.social + 10.0)
            target_stats.social = min(100.0, target_stats.social + 10.0)

        from ..engine.event_bus import EventBus
        from .events import SocialInteractionEvent

        event_bus = self.world.services.try_get(EventBus)
        if event_bus:
            event_bus.publish(SocialInteractionEvent(initiator_id, target_id, interaction_type))

        return True
