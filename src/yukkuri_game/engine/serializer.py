"""
Serialization Module.
"""
from typing import Any, Dict, Type, Optional, Iterable
import msgspec
from loguru import logger
from .ecs import World
from .migration import MigrationRegistry

class WorldSerializer:
    """
    Handles serialization and deserialization of the game world.
    """
    def __init__(self, world: World, component_types: Iterable[Type[Any]]):
        self.world = world
        self.component_map = {c.__name__: c for c in component_types}
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
            # Skip components that shouldn't be serialized
            if component_type.__name__ == "PhysicsBody":
                continue

            # Avoid serializing StableIDComponent twice (it's in stable_id field)
            if self._stable_id_type and component_type == self._stable_id_type:
                continue

            try:
                # Using msgspec for efficient serialization if it's a struct/dataclass
                if hasattr(component, "__dataclass_fields__") or isinstance(component, msgspec.Struct):
                    decoded = msgspec.to_builtins(component)
                    # Add version info if available
                    if hasattr(component_type, "_version_"):
                         decoded["_version_"] = getattr(component_type, "_version_")
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
                        # Check migration
                        saved_version = comp_data.pop("_version_", 0)
                        target_version = getattr(comp_class, "_version_", 0)

                        if saved_version < target_version:
                            comp_data = MigrationRegistry.migrate(comp_name, comp_data, saved_version, target_version)

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
                # Heuristic: Check all fields if no explicit _references definition
                # Or adhere strictly to _references if defined.
                # The critique suggested applying a heuristic to avoid corruption if _references isn't used everywhere.
                # However, the previous code ONLY looked at _references.
                # The critique implies "It iterates over *all* fields...".
                # Wait, the previous code `if hasattr(component, "_references")` means it WAS safe IF `_references` was used.
                # But maybe the critique implies I should use a heuristic INSTEAD or IN ADDITION because `_references` might be missing?
                # "It iterates over *all* fields of a component and replaces any integer value..." -
                # My previous code: `if hasattr(component, "_references"): ref_fields = getattr(component, "_references")`
                # So it ONLY iterated over `_references`.
                # BUT, `AIState` for example might not have `_references` defined but has `current_target_id`.
                # If I want to be safe and robust without manually annotating every component with `_references`, I should use the heuristic on ALL components.

                # Let's switch to iterating all fields (dataclasses) and applying the heuristic,
                # OR using _references if present.
                # The critique provided a patch that iterates dataclass fields.

                if hasattr(component, "__dataclass_fields__"):
                    for field_name in component.__dataclass_fields__:
                        # Check if this field should be remapped
                        # 1. Explicit _references
                        is_ref = False
                        if hasattr(component, "_references") and field_name in getattr(component, "_references"):
                            is_ref = True

                        # 2. Heuristic
                        if not is_ref:
                            if field_name.endswith("_id") or field_name.endswith("_ids") or field_name in ("parent", "owner", "target"):
                                is_ref = True

                        if not is_ref:
                            continue

                        val = getattr(component, field_name)

                        # Remap logic
                        if isinstance(val, int):
                            if val in id_map:
                                setattr(component, field_name, id_map[val])
                        elif isinstance(val, list):
                            new_list = [id_map.get(x, x) if isinstance(x, int) else x for x in val]
                            setattr(component, field_name, new_list)
                        elif isinstance(val, set):
                            new_set = {id_map.get(x, x) if isinstance(x, int) else x for x in val}
                            setattr(component, field_name, new_set)
                        elif isinstance(val, dict):
                            new_dict = {id_map.get(k, k) if isinstance(k, int) else k: v for k, v in val.items()}
                            setattr(component, field_name, new_dict)

        logger.info(f"Loaded {len(entities_data)} entities from {filepath}")
