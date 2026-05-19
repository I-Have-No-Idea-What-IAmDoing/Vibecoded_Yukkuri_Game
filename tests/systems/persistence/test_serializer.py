import pytest
import os
import sqlite3
import msgspec
import dataclasses
from dataclasses import dataclass, field
from typing import Dict
from yukkuri_game.engine.ecs import World
from yukkuri_game.engine.serializer import WorldSerializer
from yukkuri_game.engine.components import StableIDComponent, Persistable
from yukkuri_game.engine.components import Transform, Selectable
from yukkuri_game.engine.types import EntityID


@dataclasses.dataclass
class SampleComponent:
    value: int
    name: str


def test_msgpack_persistence(tmp_path):
    world = World()

    # Create an entity
    entity = world.create_entity()
    world.add_component(entity, StableIDComponent(id=1))
    world.add_component(entity, Persistable())
    world.add_component(entity, Transform(x=10, y=20))
    world.add_component(entity, Selectable(selected=True))

    # Setup serializer
    comp_types = [
        StableIDComponent,
        Persistable,
        Transform,
        Selectable,
        SampleComponent,
    ]
    serializer = WorldSerializer(world, comp_types)

    filepath = str(tmp_path / "test_save.sqlite")
    import sqlite3

    # Save
    conn = sqlite3.connect(filepath)
    serializer.save_to_sqlite(conn)
    conn.commit()
    conn.close()

    # Check if file exists
    assert os.path.exists(filepath)

    # Read file content and verify MessagePack
    conn = sqlite3.connect(filepath)
    cursor = conn.cursor()
    cursor.execute("SELECT data FROM chunks")
    data = cursor.fetchone()[0]
    decoded_data = msgspec.msgpack.decode(data)
    conn.close()

    assert isinstance(decoded_data, list)
    assert len(decoded_data) == 1
    entity_data = decoded_data[0]

    assert entity_data["stable_id"] == 1
    assert "Transform" in entity_data["components"]
    assert "Selectable" in entity_data["components"]
    assert (
        "StableIDComponent" not in entity_data["components"]
    )  # Verification of optimization

    assert entity_data["components"]["Transform"]["x"] == 10.0

    # Load into new world
    new_world = World()
    new_serializer = WorldSerializer(new_world, comp_types)
    conn = sqlite3.connect(filepath)
    new_serializer.load_from_sqlite(conn)
    conn.close()

    # Verify entity loaded
    assert len(new_world.get_all_entities()) == 1
    new_entity = list(new_world.get_all_entities())[0]

    stable_id = new_world.get_component(new_entity, StableIDComponent)
    assert stable_id.id == 1

    transform = new_world.get_component(new_entity, Transform)
    assert transform.x == 10.0

    selectable = new_world.get_component(new_entity, Selectable)
    assert selectable.selected

    # Cleanup
    if os.path.exists(filepath):
        os.remove(filepath)

@dataclass
class SafeRefComponent:
    entity_id: EntityID = EntityID(-1)
    target_id: EntityID = EntityID(-1)
    sprite_id: int = 0  # Should NOT be remapped implicitly


@dataclass
class DictComponent:
    threats: Dict[EntityID, int] = field(
        default_factory=dict
    )  # Key=ID, Value=Amount. Should remap Key.
    metadata: Dict[EntityID, str] = field(
        default_factory=dict
    )  # Key=ID, Value=String. Should remap Key.

    # _references = {"threats", "metadata"} # Removed as we use type introspection now


class TestSerializerFix:
    @pytest.fixture(autouse=True)
    def setup_and_teardown(self, tmp_path):
        self.world = World()
        self.serializer = WorldSerializer(
            self.world,
            [SafeRefComponent, DictComponent, StableIDComponent, Persistable],
        )
        self.filepath = str(tmp_path / "test_serializer_fix.sqlite")
        yield
        if os.path.exists(self.filepath):
            os.remove(self.filepath)

    def test_safe_ref_remapping(self) -> None:
        target = self.world.create_entity()
        self.world.add_component(target, StableIDComponent(id=100))
        self.world.add_component(target, Persistable())

        source = self.world.create_entity()
        self.world.add_component(source, StableIDComponent(id=200))
        self.world.add_component(source, Persistable())

        comp = SafeRefComponent(entity_id=source, target_id=target, sprite_id=target)
        original_target_id = target

        self.world.add_component(source, comp)
        conn = sqlite3.connect(self.filepath)
        self.serializer.save_to_sqlite(conn)
        conn.commit()
        conn.close()
        self.world.clear_database()

        conn = sqlite3.connect(self.filepath)
        self.serializer.load_from_sqlite(conn)
        conn.close()

        entities = self.world.get_all_entities()
        new_source = None
        new_target = None
        for e in entities:
            if self.world.has_component(e, SafeRefComponent):
                new_source = e
            else:
                new_target = e

        loaded_comp = self.world.get_component(new_source, SafeRefComponent)

        assert loaded_comp.target_id == new_target
        assert loaded_comp.entity_id == new_source
        assert loaded_comp.sprite_id == original_target_id

    def test_dict_remapping(self) -> None:
        e1 = self.world.create_entity()
        self.world.add_component(e1, StableIDComponent(id=10))
        self.world.add_component(e1, Persistable())

        e2 = self.world.create_entity()
        self.world.add_component(e2, StableIDComponent(id=20))
        self.world.add_component(e2, Persistable())

        # e1 has a threat table pointing to e2. Threat amount is coincidentally e2's ID.
        threat_val = e2
        comp = DictComponent(threats={e2: threat_val}, metadata={e2: "Enemy"})
        self.world.add_component(e1, comp)

        conn = sqlite3.connect(self.filepath)
        self.serializer.save_to_sqlite(conn)
        conn.commit()
        conn.close()
        self.world.clear_database()

        # Shift IDs
        dummy = self.world.create_entity()

        conn = sqlite3.connect(self.filepath)
        self.serializer.load_from_sqlite(conn)
        conn.close()

        entities = self.world.get_all_entities()
        new_e1 = None
        new_e2 = None

        for e in entities:
            if self.world.has_component(e, DictComponent):
                new_e1 = e
            elif e != dummy:
                new_e2 = e

        assert new_e1 is not None
        assert new_e2 is not None

        loaded_comp = self.world.get_component(new_e1, DictComponent)

        # Check Key Remapping
        assert new_e2 in loaded_comp.threats
        assert new_e2 in loaded_comp.metadata

        # Check Value Preservation (Should NOT remap value)
        # Original value was 'threat_val' (original e2 ID).
        # It should remain 'threat_val'.
        assert loaded_comp.threats[new_e2] == threat_val
        assert loaded_comp.threats[new_e2] != new_e2
