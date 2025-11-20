import uuid
from typing import Dict, Any, Type, Optional, List

class Component:
    """Base class for all components."""
    pass

class Entity:
    """A generic entity that holds components."""
    def __init__(self, entity_id: str = None):
        self.id = entity_id or str(uuid.uuid4())
        self.components: Dict[Type[Component], Component] = {}
        self.marked_for_destruction = False

    def add_component(self, component: Component):
        self.components[type(component)] = component
        return self

    def get_component(self, component_type: Type[Component]) -> Optional[Component]:
        return self.components.get(component_type)

    def has_component(self, component_type: Type[Component]) -> bool:
        return component_type in self.components

    def remove_component(self, component_type: Type[Component]):
        if component_type in self.components:
            del self.components[component_type]

class System:
    """Base class for all systems."""
    def update(self, delta_time: float, entities: List[Entity], game_state: Any):
        raise NotImplementedError

class EntityManager:
    """Manages entities and systems."""
    def __init__(self):
        self.entities: List[Entity] = []
        self.systems: List[System] = []

    def add_entity(self, entity: Entity):
        self.entities.append(entity)

    def remove_entity(self, entity: Entity):
        if entity in self.entities:
            self.entities.remove(entity)

    def add_system(self, system: System):
        self.systems.append(system)

    def update(self, delta_time: float, game_state: Any):
        # Update systems
        for system in self.systems:
            system.update(delta_time, self.entities, game_state)

        # Cleanup
        self.entities = [e for e in self.entities if not e.marked_for_destruction]

    def get_entities_with_component(self, component_type: Type[Component]) -> List[Entity]:
        return [e for e in self.entities if e.has_component(component_type)]
