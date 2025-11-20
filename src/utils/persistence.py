import json
import os
from typing import Dict, Any
from src.engine.ecs import EntityManager, Entity
from src.engine.components import Transform, Stats, Identity, AIComponent, ItemComponent
from src.utils.loader import game_data

class Persistence:
    def __init__(self, save_dir: str = "saves"):
        self.save_dir = save_dir
        os.makedirs(self.save_dir, exist_ok=True)

    def save_game(self, game: Any, filename: str = "savegame.json"):
        data = {
            "state": {
                "money": game.state.money,
                "time_elapsed": game.state.time_elapsed,
                "day_count": game.state.day_count,
                "camera_x": game.state.camera_x,
                "camera_y": game.state.camera_y,
                "zoom": game.state.zoom
            },
            "entities": []
        }

        for entity in game.ecs.entities:
            entity_data = {"id": entity.id, "components": {}}

            # Serialize Components
            # Transform
            t = entity.get_component(Transform)
            if t:
                entity_data["components"]["transform"] = {
                    "x": t.x, "y": t.y, "width": t.width, "height": t.height,
                    "vx": t.vx, "vy": t.vy
                }

            # Stats
            s = entity.get_component(Stats)
            if s:
                entity_data["components"]["stats"] = {
                    "health": s.health, "max_health": s.max_health,
                    "hunger": s.hunger, "max_hunger": s.max_hunger,
                    "happiness": s.happiness, "max_happiness": s.max_happiness,
                    "energy": s.energy, "max_energy": s.max_energy,
                    "cleanliness": s.cleanliness, "max_cleanliness": s.max_cleanliness,
                    "age": s.age, "growth_stage": s.growth_stage,
                    "quality_score": s.quality_score, "badges": s.badges
                }

            # Identity
            i = entity.get_component(Identity)
            if i:
                entity_data["components"]["identity"] = {
                    "name": i.name, "type_id": i.type_id, "color": i.color
                }

            # AI
            ai = entity.get_component(AIComponent)
            if ai:
                 entity_data["components"]["ai"] = {
                     "current_action": ai.current_action,
                     "action_timer": ai.action_timer,
                     # Cooldowns are transient enough to skip for MVP, but let's keep them
                     "action_cooldowns": ai.action_cooldowns
                 }

            # Item
            item = entity.get_component(ItemComponent)
            if item:
                entity_data["components"]["item"] = {
                    "item_type": item.item_type,
                    "value": item.value,
                    "cost": item.cost
                }

            data["entities"].append(entity_data)

        filepath = os.path.join(self.save_dir, filename)
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)
        print(f"Game saved to {filepath}")

    def load_game(self, game: Any, filename: str = "savegame.json"):
        filepath = os.path.join(self.save_dir, filename)
        if not os.path.exists(filepath):
            print(f"Save file {filepath} not found.")
            return

        with open(filepath, "r") as f:
            data = json.load(f)

        # Load State
        state_data = data.get("state", {})
        game.state.money = state_data.get("money", 0)
        game.state.time_elapsed = state_data.get("time_elapsed", 0)
        game.state.day_count = state_data.get("day_count", 1)
        game.state.camera_x = state_data.get("camera_x", 0)
        game.state.camera_y = state_data.get("camera_y", 0)
        game.state.zoom = state_data.get("zoom", 1.0)

        # Load Entities
        game.ecs.entities = [] # Clear existing

        for e_data in data.get("entities", []):
            entity = Entity(e_data.get("id"))
            comps = e_data.get("components", {})

            if "transform" in comps:
                c = comps["transform"]
                entity.add_component(Transform(
                    x=c["x"], y=c["y"], width=c["width"], height=c["height"],
                    vx=c.get("vx", 0), vy=c.get("vy", 0)
                ))

            if "stats" in comps:
                c = comps["stats"]
                entity.add_component(Stats(
                    health=c["health"], max_health=c["max_health"],
                    hunger=c["hunger"], max_hunger=c["max_hunger"],
                    happiness=c["happiness"], max_happiness=c["max_happiness"],
                    energy=c["energy"], max_energy=c["max_energy"],
                    cleanliness=c.get("cleanliness", 100.0), max_cleanliness=c.get("max_cleanliness", 100.0),
                    age=c["age"], growth_stage=c["growth_stage"],
                    quality_score=c["quality_score"], badges=c["badges"]
                ))

            if "identity" in comps:
                c = comps["identity"]
                # Fix color tuple loaded as list
                color = tuple(c["color"])
                entity.add_component(Identity(
                    name=c["name"], type_id=c["type_id"], color=color
                ))

            if "ai" in comps:
                c = comps["ai"]
                entity.add_component(AIComponent(
                    current_action=c["current_action"],
                    action_timer=c["action_timer"],
                    action_cooldowns=c.get("action_cooldowns", {})
                ))

            if "item" in comps:
                c = comps["item"]
                entity.add_component(ItemComponent(
                    item_type=c["item_type"], value=c["value"], cost=c["cost"]
                ))

            game.ecs.add_entity(entity)

        print(f"Game loaded from {filepath}")
