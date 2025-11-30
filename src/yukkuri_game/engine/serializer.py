"""
Serialization Module.
"""
from typing import Any, Dict, Type, Optional, Iterable
import msgspec
import json
from loguru import logger
from .ecs import World

# Registry for custom serializers/deserializers if needed
# For now, we assume simple dataclasses

class WorldSerializer:
    """
    Handles serialization and deserialization of the game world.
    """
    def __init__(self, world: World, component_types: Iterable[Type[Any]]):
        self.world = world
        self.component_map = {c.__name__: c for c in component_types}
        # We need to know Persistable and StableIDComponent types to identify them.
        # We can look them up by name in the map, or require them explicitly?
        # For decoupled design, we look up by name.
        self._persistable_type = self.component_map.get("Persistable")
        self._stable_id_type = self.component_map.get("StableIDComponent")

    def serialize_entity(self, entity: int) -> Optional[Dict[str, Any]]:
        """
        Serializes a single entity.
        Returns a dict containing 'stable_id', 'components'.
        """
        if not self._persistable_type or not self.world.has_component(entity, self._persistable_type):
            return None

        stable_id = None
        if self._stable_id_type:
             stable_id_comp = self.world.try_get_component(entity, self._stable_id_type)
             stable_id = stable_id_comp.id if stable_id_comp else None

        components_data = {}
        # Use get_all_components to retrieve all components for the entity
        all_components = self.world.get_all_components(entity)

        for component in all_components:
            component_type = type(component)
            # Skip components that shouldn't be serialized or handle them specially
            # For now, we skip if it's not a dataclass or basic type
            # We also skip PhysicsBody as it is runtime state (recreated from Transform/Stats)
            if component_type.__name__ == "PhysicsBody":
                continue

            try:
                # Using msgspec for efficient serialization if it's a struct/dataclass
                # Or just simple dict conversion if possible
                if hasattr(component, "__dataclass_fields__") or isinstance(component, msgspec.Struct):
                    # Simple workaround: use msgspec tojson then fromjson to get a clean dict
                    # Or better, msgspec.to_builtins
                    # But msgspec.to_builtins requires a defined schema usually.
                    # Let's try msgspec.json.encode -> decode
                    encoded = msgspec.json.encode(component)
                    decoded = msgspec.json.decode(encoded)
                    components_data[component_type.__name__] = decoded
                else:
                    # Fallback or skip
                    pass
            except Exception as e:
                logger.warning(f"Failed to serialize component {component_type.__name__} for entity {entity}: {e}")

        return {
            "stable_id": stable_id,
            "components": components_data
        }

    def save_to_file(self, filepath: str):
        """Saves all persistable entities to a file."""
        if not self._persistable_type:
            logger.warning("Persistable component type not registered. Cannot save.")
            return

        entities_data = []
        # Query all entities with Persistable
        # self.world.get_components returns Dict[entity, component]
        for entity, _ in self.world.get_components(self._persistable_type).items():
            data = self.serialize_entity(entity)
            if data:
                entities_data.append(data)

        with open(filepath, "w") as f:
            json.dump(entities_data, f, indent=2)
        logger.info(f"Saved {len(entities_data)} entities to {filepath}")

    def load_from_file(self, filepath: str):
        """
        Loads entities from a file.
        """
        try:
            with open(filepath, "r") as f:
                entities_data = json.load(f)
        except FileNotFoundError:
            logger.error(f"Save file {filepath} not found.")
            return

        for entity_data in entities_data:
            stable_id = entity_data.get("stable_id")
            components_data = entity_data.get("components", {})

            # Create entity
            entity = self.world.create_entity()

            # Add StableID if exists
            if stable_id and self._stable_id_type:
                self.world.add_component(entity, self._stable_id_type(id=stable_id))

            for comp_name, comp_data in components_data.items():
                comp_class = self.component_map.get(comp_name)
                if comp_class:
                    try:
                        # Attempt to instantiate dataclass/struct from dict
                        # This works for simple dataclasses.
                        # Complex nested types might need msgspec.convert
                        component = msgspec.convert(comp_data, comp_class)
                        self.world.add_component(entity, component)
                    except Exception as e:
                        logger.warning(f"Failed to deserialize component {comp_name}: {e}")
                else:
                    logger.warning(f"Unknown component type: {comp_name}")

            # Post-load hooks?
            # e.g. Recreate PhysicsBody from Transform/Stats
            # This logic should typically be in a System or a "PostLoad" phase.
            # For now we leave it as data-only.

        logger.info(f"Loaded {len(entities_data)} entities from {filepath}")
