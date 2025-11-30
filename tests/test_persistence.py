
import pytest
import os
import shutil
from yukkuri_game.engine.ecs import World
from yukkuri_game.engine.serializer import WorldSerializer
from yukkuri_game.game.prefabs.yukkuri import create_yukkuri
from yukkuri_game.game.components_persistence import StableIDComponent, Persistable
from yukkuri_game.game.components import Transform, PhysicsBody
from yukkuri_game.game.yukkuri_components import YukkuriStats
from yukkuri_game.engine.resource_manager import ResourceManager
from yukkuri_game.game.systems.physics import PhysicsSystem
from yukkuri_game.game.systems.physics_reconstruction import reconstruct_physics
import inspect
from yukkuri_game.game import components, yukkuri_components, components_persistence

# Mock ResourceManager and other dependencies if needed
class MockResourceManager:
    def __init__(self):
        self.yukkuri_types = {
            "reimu": {
                "image": "reimu.png",
                "max_health": 100
            }
        }
        self.tuning = None

def test_persistence():
    # Setup World
    world = World()
    rm = MockResourceManager()
    world.services.register(rm, ResourceManager)
    physics_system = PhysicsSystem()
    world.services.register(physics_system, PhysicsSystem)

    # Create Entity
    entity = create_yukkuri(world, "reimu", 100, 200)

    # Verify components
    assert world.has_component(entity, StableIDComponent)
    assert world.has_component(entity, Persistable)
    assert world.has_component(entity, Transform)

    stable_id = world.get_component(entity, StableIDComponent).id

    # Save
    comp_types = []
    for module in [components, yukkuri_components, components_persistence]:
        for _, obj in inspect.getmembers(module):
            if inspect.isclass(obj):
                    comp_types.append(obj)

    serializer = WorldSerializer(world, comp_types)
    test_file = "test_save.json"
    serializer.save_to_file(test_file)

    assert os.path.exists(test_file)

    # Clear World
    world.clear()
    assert not world.entity_exists(entity)

    # Load
    serializer.load_from_file(test_file)
    reconstruct_physics(world)

    # Verify Loaded Entity
    # We need to find the entity with the same StableID
    found_entity = None
    for e, comp in world.get_components(StableIDComponent).items():
        if comp.id == stable_id:
            found_entity = e
            break

    assert found_entity is not None

    # Verify Data
    transform = world.get_component(found_entity, Transform)
    assert transform.x == 100
    assert transform.y == 200

    stats = world.get_component(found_entity, YukkuriStats)
    assert stats.type_id == "reimu"
    # Baby yukkuri has half health (50)
    assert stats.max_health == 50.0

    # Verify Physics
    assert world.has_component(found_entity, PhysicsBody)
    pb = world.get_component(found_entity, PhysicsBody)
    assert pb.body.position.x == 100
    assert pb.body.position.y == 200

    # Cleanup
    if os.path.exists(test_file):
        os.remove(test_file)

if __name__ == "__main__":
    test_persistence()
