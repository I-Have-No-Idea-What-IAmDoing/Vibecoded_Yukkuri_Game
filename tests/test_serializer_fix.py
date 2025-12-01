import unittest
import os
from dataclasses import dataclass, field
from typing import Set, Dict, List, Any
from src.yukkuri_game.engine.ecs import World
from src.yukkuri_game.engine.serializer import WorldSerializer
from src.yukkuri_game.game.components_persistence import StableIDComponent, Persistable

@dataclass
class SafeRefComponent:
    entity_id: int = -1
    target_id: int = -1
    sprite_id: int = 0  # Should NOT be remapped implicitly

@dataclass
class DictComponent:
    threats: Dict[int, int] = field(default_factory=dict) # Key=ID, Value=Amount. Should remap Key.
    metadata: Dict[int, str] = field(default_factory=dict) # Key=ID, Value=String. Should remap Key.

class TestSerializerFix(unittest.TestCase):
    def setUp(self):
        self.world = World()
        self.serializer = WorldSerializer(self.world, [SafeRefComponent, DictComponent, StableIDComponent, Persistable])
        self.filepath = "test_serializer_fix.msgpack"

    def tearDown(self):
        if os.path.exists(self.filepath):
            os.remove(self.filepath)

    def test_safe_ref_remapping(self):
        target = self.world.create_entity()
        self.world.add_component(target, StableIDComponent(id=100))
        self.world.add_component(target, Persistable())

        source = self.world.create_entity()
        self.world.add_component(source, StableIDComponent(id=200))
        self.world.add_component(source, Persistable())

        comp = SafeRefComponent(entity_id=source, target_id=target, sprite_id=target)
        original_target_id = target

        self.world.add_component(source, comp)
        self.serializer.save_to_file(self.filepath)
        self.world.clear_database()

        self.serializer.load_from_file(self.filepath)

        entities = self.world.get_all_entities()
        new_source = None
        new_target = None
        for e in entities:
            if self.world.has_component(e, SafeRefComponent):
                new_source = e
            else:
                new_target = e

        loaded_comp = self.world.get_component(new_source, SafeRefComponent)

        self.assertEqual(loaded_comp.target_id, new_target)
        self.assertEqual(loaded_comp.entity_id, new_source)
        self.assertEqual(loaded_comp.sprite_id, original_target_id)

    def test_dict_remapping(self):
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

        self.serializer.save_to_file(self.filepath)
        self.world.clear_database()

        # Shift IDs
        dummy = self.world.create_entity()

        self.serializer.load_from_file(self.filepath)

        entities = self.world.get_all_entities()
        new_e1 = None
        new_e2 = None

        for e in entities:
            if self.world.has_component(e, DictComponent):
                new_e1 = e
            elif e != dummy:
                new_e2 = e

        self.assertIsNotNone(new_e1)
        self.assertIsNotNone(new_e2)

        loaded_comp = self.world.get_component(new_e1, DictComponent)

        # Check Key Remapping
        self.assertIn(new_e2, loaded_comp.threats)
        self.assertIn(new_e2, loaded_comp.metadata)

        # Check Value Preservation (Should NOT remap value)
        # Original value was 'threat_val' (original e2 ID).
        # It should remain 'threat_val'.
        self.assertEqual(loaded_comp.threats[new_e2], threat_val)
        self.assertNotEqual(loaded_comp.threats[new_e2], new_e2)

if __name__ == '__main__':
    unittest.main()
