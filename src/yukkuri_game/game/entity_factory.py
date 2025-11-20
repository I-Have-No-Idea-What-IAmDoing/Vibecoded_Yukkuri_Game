from ..engine.ecs import World
from .components import Transform, Sprite, Selectable
from .yukkuri_components import YukkuriStats, AIState, ItemStats

class EntityFactory:
    def __init__(self, world: World, resource_manager):
        self.world = world
        self.rm = resource_manager

    def create_yukkuri(self, type_id: str, x: float, y: float) -> int:
        data = self.rm.yukkuri_types.get(type_id)
        if not data:
            raise ValueError(f"Unknown yukkuri type: {type_id}")

        entity = self.world.create_entity()

        # Core Components
        self.world.add_component(entity, Transform(x=x, y=y))
        self.world.add_component(entity, Sprite(
            image_name=data.get("image", "yukkuri_default.png"),
            width=data.get("width", 64),
            height=data.get("height", 64)
        ))
        self.world.add_component(entity, Selectable())

        # Yukkuri Stats
        stats = YukkuriStats(
            name=f"{type_id}_{entity}",
            type_id=type_id,
            max_health=data.get("max_health", 100),
            health=data.get("max_health", 100)
        )
        self.world.add_component(entity, stats)

        # AI
        self.world.add_component(entity, AIState())

        return entity

    def create_item(self, type_id: str, x: float, y: float) -> int:
        data = self.rm.item_types.get(type_id)
        if not data:
            raise ValueError(f"Unknown item type: {type_id}")

        entity = self.world.create_entity()

        self.world.add_component(entity, Transform(x=x, y=y))
        self.world.add_component(entity, Sprite(
            image_name=data.get("image", "item_default.png"),
            width=data.get("width", 32),
            height=data.get("height", 32)
        ))
        self.world.add_component(entity, Selectable())

        stats = ItemStats(
            name=data.get("name", "Item"),
            type_id=type_id,
            cost=data.get("cost", 10),
            nutrition=data.get("nutrition", 0),
            fun=data.get("fun", 0),
            comfort=data.get("comfort", 0),
            is_portable=data.get("is_portable", False)
        )
        self.world.add_component(entity, stats)

        return entity
