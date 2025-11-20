from typing import Type, TypeVar, Dict, Any, List, Optional
import uuid

T = TypeVar('T')

class Component:
    """Base class for components, though not strictly required by this ECS implementation."""
    pass

class World:
    def __init__(self):
        self._entities: List[int] = []
        self._components: Dict[Type, Dict[int, Any]] = {}
        self._next_entity_id = 0
        self._systems = []

    def create_entity(self) -> int:
        entity = self._next_entity_id
        self._next_entity_id += 1
        self._entities.append(entity)
        return entity

    def destroy_entity(self, entity: int):
        if entity in self._entities:
            self._entities.remove(entity)
            for c_type in self._components:
                if entity in self._components[c_type]:
                    del self._components[c_type][entity]

    def add_component(self, entity: int, component: Any):
        c_type = type(component)
        if c_type not in self._components:
            self._components[c_type] = {}
        self._components[c_type][entity] = component

    def remove_component(self, entity: int, component_type: Type):
        if component_type in self._components and entity in self._components[component_type]:
            del self._components[component_type][entity]

    def get_component(self, entity: int, component_type: Type[T]) -> Optional[T]:
        return self._components.get(component_type, {}).get(entity)

    def has_component(self, entity: int, component_type: Type) -> bool:
        return entity in self._components.get(component_type, {})

    def get_components(self, component_type: Type[T]) -> Dict[int, T]:
        return self._components.get(component_type, {})

    def get_entities_with(self, *component_types: Type) -> List[int]:
        if not component_types:
            return []

        # Start with entities having the first component
        first_type = component_types[0]
        entities = set(self._components.get(first_type, {}).keys())

        for c_type in component_types[1:]:
            entities &= set(self._components.get(c_type, {}).keys())

        return list(entities)

    def add_system(self, system):
        self._systems.append(system)

    def update(self, dt: float):
        for system in self._systems:
            system.update(self, dt)

class System:
    def update(self, world: World, dt: float):
        raise NotImplementedError
