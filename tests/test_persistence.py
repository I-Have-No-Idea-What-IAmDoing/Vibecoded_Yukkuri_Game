import pytest
import os
import msgspec
import dataclasses
from src.yukkuri_game.engine.ecs import World
from src.yukkuri_game.engine.serializer import WorldSerializer
from src.yukkuri_game.game.components_persistence import StableIDComponent, Persistable
from src.yukkuri_game.game.components import Transform, Selectable

@dataclasses.dataclass
class TestComponent:
    value: int
    name: str

def test_msgpack_persistence():
    world = World()

    # Create an entity
    entity = world.create_entity()
    world.add_component(entity, StableIDComponent(id="test-uuid"))
    world.add_component(entity, Persistable())
    world.add_component(entity, Transform(x=10, y=20))
    world.add_component(entity, Selectable(selected=True))

    # Setup serializer
    comp_types = [StableIDComponent, Persistable, Transform, Selectable, TestComponent]
    serializer = WorldSerializer(world, comp_types)

    filepath = "test_save.msgpack"

    # Save
    serializer.save_to_file(filepath)

    # Check if file exists
    assert os.path.exists(filepath)

    # Read file content and verify MessagePack
    with open(filepath, "rb") as f:
        data = f.read()
        decoded_data = msgspec.msgpack.decode(data)

    assert isinstance(decoded_data, list)
    assert len(decoded_data) == 1
    entity_data = decoded_data[0]

    assert entity_data["stable_id"] == "test-uuid"
    assert "Transform" in entity_data["components"]
    assert "Selectable" in entity_data["components"]
    assert "StableIDComponent" not in entity_data["components"] # Verification of optimization

    assert entity_data["components"]["Transform"]["x"] == 10.0

    # Load into new world
    new_world = World()
    new_serializer = WorldSerializer(new_world, comp_types)
    new_serializer.load_from_file(filepath)

    # Verify entity loaded
    assert len(new_world.get_all_entities()) == 1
    new_entity = list(new_world.get_all_entities())[0]

    stable_id = new_world.get_component(new_entity, StableIDComponent)
    assert stable_id.id == "test-uuid"

    transform = new_world.get_component(new_entity, Transform)
    assert transform.x == 10.0

    selectable = new_world.get_component(new_entity, Selectable)
    assert selectable.selected == True

    # Cleanup
    if os.path.exists(filepath):
        os.remove(filepath)
