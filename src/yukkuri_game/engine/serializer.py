"""
Serialization Module.
"""
from typing import Any, Dict, Type, Optional, Iterable
import msgspec
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
        Returns a dict containing 'entity_id', 'stable_id', 'components'.
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
                if hasattr(component, "__dataclass_fields__") or isinstance(component, msgspec.Struct):
                    # Convert to python builtins (dict/list/etc) which msgspec.msgpack can encode
                    decoded = msgspec.to_builtins(component)
                    components_data[component_type.__name__] = decoded
                else:
                    # Fallback or skip
                    pass
            except Exception as e:
                logger.warning(f"Failed to serialize component {component_type.__name__} for entity {entity}: {e}")

        return {
            "entity_id": entity,
            "stable_id": stable_id,
            "components": components_data
        }

    def save_to_file(self, filepath: str):
        """Saves all persistable entities to a file using MessagePack."""
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

        with open(filepath, "wb") as f:
            f.write(msgspec.msgpack.encode(entities_data))
        logger.info(f"Saved {len(entities_data)} entities to {filepath}")

    def load_from_file(self, filepath: str):
        """
        Loads entities from a file using MessagePack with two-pass reference resolution.
        """
        try:
            with open(filepath, "rb") as f:
                data = f.read()
                entities_data = msgspec.msgpack.decode(data)
        except FileNotFoundError:
            logger.error(f"Save file {filepath} not found.")
            return

        # Pass 1: Create Entities and Mapping
        id_map: Dict[int, int] = {} # old_id -> new_id

        for entity_data in entities_data:
            old_id = entity_data.get("entity_id")
            stable_id = entity_data.get("stable_id")
            components_data = entity_data.get("components", {})

            # Create new entity
            new_entity = self.world.create_entity()
            if old_id is not None:
                id_map[old_id] = new_entity

            # Add StableID if exists
            if stable_id and self._stable_id_type:
                self.world.add_component(new_entity, self._stable_id_type(id=stable_id))

            for comp_name, comp_data in components_data.items():
                comp_class = self.component_map.get(comp_name)
                if comp_class:
                    try:
                        component = msgspec.convert(comp_data, comp_class)
                        self.world.add_component(new_entity, component)
                    except Exception as e:
                        logger.warning(f"Failed to deserialize component {comp_name}: {e}")
                else:
                    logger.warning(f"Unknown component type: {comp_name}")

        # Pass 2: Resolve References
        for new_entity in id_map.values():
            all_components = self.world.get_all_components(new_entity)
            for component in all_components:
                if hasattr(component, "_references"):
                    ref_fields = getattr(component, "_references")
                    for field_name in ref_fields:
                        if not hasattr(component, field_name):
                            continue

                        val = getattr(component, field_name)

                        # Remap logic
                        if isinstance(val, int):
                            if val in id_map:
                                setattr(component, field_name, id_map[val])
                        elif isinstance(val, list):
                            # Assume list of IDs
                            new_list = [id_map.get(x, x) if isinstance(x, int) else x for x in val]
                            setattr(component, field_name, new_list)
                        elif isinstance(val, set):
                            new_set = {id_map.get(x, x) if isinstance(x, int) else x for x in val}
                            setattr(component, field_name, new_set)
                        elif isinstance(val, dict):
                            # Assume keys are IDs
                            new_dict = {id_map.get(k, k) if isinstance(k, int) else k: v for k, v in val.items()}
                            setattr(component, field_name, new_dict)

        logger.info(f"Loaded {len(entities_data)} entities from {filepath}")
