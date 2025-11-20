import esper
from typing import Type, TypeVar, Optional, List, Any, Tuple

class Component:
    """
    Base class for components.
    Not required by esper, but kept for compatibility with existing code.
    """
    pass

# Wrapper for esper to provide a World class interface
class World:
    """
    A wrapper around esper module-level functions to provide an object-oriented World interface.
    This assumes a single world context (global state in esper 3.x).
    """
    def __init__(self):
        # In esper 3.x, state is global. To simulate a new world, we clear it.
        # Note: This prevents multiple worlds existing simultaneously.
        esper.clear_database()

    def create_entity(self) -> int:
        return esper.create_entity()

    def delete_entity(self, entity: int) -> None:
        esper.delete_entity(entity)

    def destroy_entity(self, entity: int) -> None:
        # Alias for compatibility if needed, though I updated callers to delete_entity mostly.
        # Check if I missed any destroy_entity calls.
        esper.delete_entity(entity)

    def add_component(self, entity: int, component: Any) -> None:
        esper.add_component(entity, component)

    def remove_component(self, entity: int, component_type: Type) -> None:
        esper.remove_component(entity, component_type)

    def component_for_entity(self, entity: int, component_type: Type) -> Any:
        return esper.component_for_entity(entity, component_type)

    def get_component(self, component_type: Type) -> List[Tuple[int, Any]]:
        # Wrapper to match esper.get_component behavior
        return esper.get_component(component_type)

    def get_components(self, *component_types: Type) -> List[Tuple]: # Variadic
         # esper 3.x get_components returns (entity, [components...])
         # We flatten it to (entity, comp1, comp2...) for easier unpacking
         raw_results = esper.get_components(*component_types)
         flattened = []
         for ent, comps in raw_results:
             flattened.append((ent, *comps))
         return flattened

    def has_component(self, entity: int, component_type: Type) -> bool:
        return esper.has_component(entity, component_type)

    def add_processor(self, processor: 'System') -> None:
        esper.add_processor(processor)
        # processor.world = self # esper.Processor doesn't seem to have .world attr auto-set in 3.x if using module functions?
        # Actually if we use module functions, we don't need self.world in processors if we call esper directly.
        # BUT my code in processors uses self.world.
        # So I need to inject it.
        processor.world = self

    def add_system(self, system: 'System') -> None:
        # Alias for compatibility
        self.add_processor(system)

    def process(self, dt: float) -> None:
        esper.process(dt)

    def entity_exists(self, entity: int) -> bool:
        return esper.entity_exists(entity)

    def clear_database(self) -> None:
        esper.clear_database()

    # Compatibility/Extensions
    @property
    def _entities(self):
        # Expose a list of entities. esper._entities is a set of IDs (if it exists) or we can inspect.
        # esper doesn't expose a simple list of all entities directly in public API.
        # But for debug HUD we need count.
        # We can access esper._entities (it is available in dir(esper))
        return list(esper._entities) if hasattr(esper, '_entities') else []

class System(esper.Processor):
    """
    A wrapper around esper.Processor.
    """
    def __init__(self):
        super().__init__()
        self.world: Optional[World] = None
