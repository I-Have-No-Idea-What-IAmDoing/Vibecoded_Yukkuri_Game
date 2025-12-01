"""
Serialization Module.
"""
from typing import Any, Dict, Type, Optional, Iterable, Set
import msgspec
from loguru import logger
from .ecs import World
from .migration import MigrationRegistry

class WorldSerializer:
    """
    Handles serialization and deserialization of the game world.
    """

    # Heuristic: Fields ending with these are considered references
    REF_SUFFIXES = ("_id", "_ids")

    # Heuristic: Exact matches for these fields
    REF_EXACT_NAMES = {"parent", "owner", "target"}

    # Blocklist: Fields that match suffixes but are definitely NOT entity references
    REF_BLOCKLIST = {
        "type_id", "sprite_id", "sound_id", "texture_id", "animation_id",
        "action_id", "behavior_id", "shader_id", "layer_id", "region_id",
        "quest_id", "dialogue_id", "scene_id", "music_id", "effect_id",
        "frame_id", "tile_id", "map_id"
    }

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

    def get_persistable_entities_data(self) -> list[Dict[str, Any]]:
        """
        Returns a list of serialized data for all persistable entities.
        """
        if not self._persistable_type:
            logger.warning("Persistable component type not registered. Cannot save.")
            return []

        entities_data = []
        for entity, _ in self.world.get_components(self._persistable_type).items():
            data = self.serialize_entity(entity)
            if data:
                entities_data.append(data)
        return entities_data

    def save_to_file(self, filepath: str):
        """Saves all persistable entities to a file using MessagePack."""
        entities_data = self.get_persistable_entities_data()
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

        self.load_from_data(entities_data)

    def load_from_data(self, entities_data: list[Dict[str, Any]]) -> None:
        """
        Loads entities from a list of entity data dicts with two-pass reference resolution.
        """
        if not entities_data:
            return

        # Pass 1: Create Entities and Mapping
        id_map: Dict[int, int] = {} # old_id -> new_id
        max_stable_id = 0

        for entity_data in entities_data:
            old_id = entity_data.get("entity_id")
            stable_id = entity_data.get("stable_id")
            components_data = entity_data.get("components", {})

            # Create new entity
            new_entity = self.world.create_entity()
            if old_id is not None:
                id_map[old_id] = new_entity

            # Add StableID if exists
            if stable_id is not None and self._stable_id_type:
                self.world.add_component(new_entity, self._stable_id_type(id=stable_id))
                if isinstance(stable_id, int):
                    max_stable_id = max(max_stable_id, stable_id)

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

        # Update World's next stable ID
        if hasattr(self.world, "set_next_stable_id"):
            self.world.set_next_stable_id(max_stable_id + 1)

        # Pass 2: Resolve References
        for new_entity in id_map.values():
            all_components = self.world.get_all_components(new_entity)
            for component in all_components:
                if hasattr(component, "__dataclass_fields__"):

                    # Determine which fields to remap
                    ref_fields: Set[str] = set()
                    is_explicit_ref = False

                    if hasattr(component, "_references"):
                         # Explicit definition takes precedence
                         ref_fields = getattr(component, "_references")
                         is_explicit_ref = True
                    else:
                        # Fallback to implicit heuristic
                        for field_name in component.__dataclass_fields__:
                            if field_name in self.REF_BLOCKLIST:
                                continue

                            if field_name in self.REF_EXACT_NAMES:
                                ref_fields.add(field_name)
                            elif field_name.endswith(self.REF_SUFFIXES):
                                ref_fields.add(field_name)

                    if not ref_fields:
                        continue

                    for field_name in ref_fields:
                        if not hasattr(component, field_name):
                             continue

                        val = getattr(component, field_name)

                        if val is not None:
                            # Handle Scalars, Lists, Sets, Dicts
                            # CRITICAL FIX: explicit check 'not isinstance(val, bool)'
                            # because in Python isinstance(True, int) is True.
                            if isinstance(val, int) and not isinstance(val, bool):
                                if val in id_map:
                                    setattr(component, field_name, id_map[val])
                                elif val > 0:
                                    # Dangling reference or false positive heuristic.
                                    is_actually_explicit = is_explicit_ref and field_name in ref_fields

                                    if is_actually_explicit:
                                        # Explicitly defined as reference, so safe to clear
                                        setattr(component, field_name, 0)
                                    else:
                                        # Heuristic. Risky. Log warning and clear.
                                        logger.warning(f"Cleared dangling reference '{field_name}'={val} in {type(component).__name__}. If this is not an entity reference, add it to REF_BLOCKLIST.")
                                        setattr(component, field_name, 0)

                            elif isinstance(val, list):
                                # Remap list items, ignoring booleans
                                new_list = []
                                for x in val:
                                    if isinstance(x, int) and not isinstance(x, bool):
                                        # Remap or clear dangling (>0 becomes 0)
                                        # Only clear if it was an entity reference, but here we can't easily warn per item?
                                        # We will apply the safe remap logic:
                                        remapped = id_map.get(x, 0 if x > 0 else x)
                                        new_list.append(remapped)
                                    else:
                                        new_list.append(x)
                                setattr(component, field_name, new_list)

                            elif isinstance(val, set):
                                new_set = {id_map.get(x, 0 if isinstance(x, int) and not isinstance(x, bool) and x > 0 else x) if isinstance(x, int) and not isinstance(x, bool) else x for x in val}
                                setattr(component, field_name, new_set)

                            elif isinstance(val, dict):
                                # Remap KEYS if they are IDs.
                                new_dict = {}
                                for k, v in val.items():
                                    if isinstance(k, int) and not isinstance(k, bool):
                                        new_k = id_map.get(k, 0 if k > 0 else k)
                                        # Fix: Prune dangling keys to avoid collision at key '0'
                                        if new_k == 0 and k > 0:
                                            continue
                                    else:
                                        new_k = k
                                    new_dict[new_k] = v
                                setattr(component, field_name, new_dict)

        logger.info(f"Loaded {len(entities_data)} entities from data")
