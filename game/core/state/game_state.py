"""
Manages the overall game state, including save/load functionality.
"""
import json
from pathlib import Path
from typing import List, Dict

from game.core.data.loader import GameData
from game.core.ecs.components import Needs, AIProfile, Position, ItemInfo, Blackboard
from game.core.ecs.entity import Entity
from game.core.sim.grid import Grid


class GameState:
    """The central manager for the game's state."""

    def __init__(self, game_data: GameData):
        self.game_data = game_data
        self.entities: List[Entity] = []
        self._next_entity_id = 0
        self.grid = Grid(20, 15)
        self.inventory: List[str] = ["bed_simple", "food_snack", "toy_ball"]

    def create_yukkuri(self, yukkuri_id: str, x: int, y: int) -> Entity:
        """Creates a new yukkuri entity."""
        yukkuri_data = self.game_data.yukkuris[yukkuri_id]
        entity = self.create_entity()
        entity.add_component(Needs(values=yukkuri_data["base_needs"].copy()))
        behavior = self.game_data.behaviors[yukkuri_data["ai_profile"]]
        entity.add_component(AIProfile(profile_id=yukkuri_data["ai_profile"], behavior=behavior))
        entity.add_component(Position(x=x, y=y))
        entity.add_component(Blackboard(data={"yukkuri_id": yukkuri_id}))
        return entity

    def create_item(self, item_id: str, x: int, y: int) -> Entity:
        """Creates a new item entity."""
        item_data = self.game_data.items[item_id]
        entity = self.create_entity()
        entity.add_component(ItemInfo(
            item_id=item_id, tags=item_data["tags"],
            effects=item_data["effects"], size=item_data["size"]
        ))
        entity.add_component(Position(x=x, y=y))
        grid_x = int(x // 40)
        grid_y = int(y // 40)
        self.grid.place(entity, grid_x, grid_y, item_data["size"]["w"], item_data["size"]["h"])
        return entity

    def create_entity(self) -> Entity:
        """Creates a new, empty entity."""
        entity = Entity(self._next_entity_id)
        self._next_entity_id += 1
        self.entities.append(entity)
        return entity

    def save_game(self, save_path: Path):
        """Saves the current game state to a file."""
        state_to_save = {
            "next_entity_id": self._next_entity_id,
            "entities": []
        }
        for entity in self.entities:
            entity_data = {"entity_id": entity.entity_id, "components": {}}
            # Yukkuri components
            if entity.has_component(Needs):
                entity_data["components"]["Needs"] = entity.get_component(Needs).values
            if entity.has_component(AIProfile):
                entity_data["components"]["AIProfile"] = entity.get_component(AIProfile).profile_id
            if entity.has_component(Blackboard):
                 entity_data["components"]["Blackboard"] = entity.get_component(Blackboard).data
            # Item components
            if entity.has_component(ItemInfo):
                 entity_data["components"]["ItemInfo"] = entity.get_component(ItemInfo).item_id
            # Shared components
            if entity.has_component(Position):
                pos = entity.get_component(Position)
                entity_data["components"]["Position"] = {"x": pos.x, "y": pos.y}

            state_to_save["entities"].append(entity_data)

        with open(save_path, "w") as f:
            json.dump(state_to_save, f, indent=4)

    def load_game(self, save_path: Path):
        """Loads the game state from a file."""
        with open(save_path, "r") as f:
            saved_state = json.load(f)

        self.entities = []
        self._next_entity_id = saved_state["next_entity_id"]
        self.grid = Grid(20, 15) # Reset grid

        for entity_data in saved_state["entities"]:
            entity = Entity(entity_data["entity_id"])
            self.entities.append(entity)
            for comp_name, comp_data in entity_data["components"].items():
                if comp_name == "Needs":
                    entity.add_component(Needs(values=comp_data))
                elif comp_name == "AIProfile":
                    behavior = self.game_data.behaviors[comp_data]
                    entity.add_component(AIProfile(profile_id=comp_data, behavior=behavior))
                elif comp_name == "Blackboard":
                    entity.add_component(Blackboard(data=comp_data))
                elif comp_name == "ItemInfo":
                    item_data = self.game_data.items[comp_data]
                    entity.add_component(ItemInfo(
                        item_id=comp_data, tags=item_data["tags"],
                        effects=item_data["effects"], size=item_data["size"]
                    ))
                elif comp_name == "Position":
                    pos = Position(x=comp_data["x"], y=comp_data["y"])
                    entity.add_component(pos)
                    if entity.has_component(ItemInfo):
                         item_info = entity.get_component(ItemInfo)
                         grid_x = int(pos.x // 40)
                         grid_y = int(pos.y // 40)
                         self.grid.place(entity, grid_x, grid_y, item_info.size["w"], item_info.size["h"])
