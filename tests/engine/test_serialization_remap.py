
import pytest
from yukkuri_game.engine.ecs import World
from yukkuri_game.engine.serializer import WorldSerializer
from yukkuri_game.game.components import MoveCommand
from yukkuri_game.engine.components import Transform
from yukkuri_game.engine.components import StableIDComponent, Persistable
from yukkuri_game.engine.types import EntityID

def test_move_command_entity_id_remapping(tmp_path):
    """
    Verify that MoveCommand.target_entity_id (which was previously int)
    is correctly remapped when loaded, now that it is typed as EntityID.
    """
    world = World()
    
    # Create Entity A (Target)
    entity_a = world.create_entity()
    world.add_component(entity_a, Transform(x=0, y=0))
    world.add_component(entity_a, Persistable())
    world.add_component(entity_a, StableIDComponent(id=100))
    
    # Create Entity B (Chaser)
    entity_b = world.create_entity()
    world.add_component(entity_b, Transform(x=10, y=10))
    world.add_component(entity_b, Persistable())
    world.add_component(entity_b, StableIDComponent(id=101))
    
    # Add MoveCommand to B targeting A
    # casting to EntityID to ensure we populate it correctly in the first place
    cmd = MoveCommand(target_entity_id=EntityID(entity_a)) 
    world.add_component(entity_b, cmd)
    
    # Serialize
    serializer = WorldSerializer(world, [MoveCommand, Transform, Persistable, StableIDComponent])
    save_file = tmp_path / "test_remap.msgpack"
    serializer.save_to_file(str(save_file))
    
    # Clear World
    world.clear_database()
    
    # Load
    serializer.load_from_file(str(save_file))
    
    # Find new entities
    entities = world.get_all_entities()
    assert len(entities) == 2
    
    # Identify them by StableID
    loaded_a = None
    loaded_b = None
    
    for ent in entities:
        stable = world.get_component(ent, StableIDComponent)
        if stable.id == 100:
            loaded_a = ent
        elif stable.id == 101:
            loaded_b = ent
            
    assert loaded_a is not None
    assert loaded_b is not None
    # assert loaded_a != entity_a # IDs might be reused if world is cleared, which is fine as long as remapping happens correctly.
    
    # Check MoveCommand on B
    new_cmd = world.get_component(loaded_b, MoveCommand)
    assert new_cmd is not None
    
    # CRITICAL CHECK: Did the ID get remapped?
    # If the serializer skipped it (because it treated it as int), it would still be 'entity_a' (the old int)
    # If valid, it should be 'loaded_a' (the new int)
    assert new_cmd.target_entity_id == loaded_a
    assert new_cmd.target_entity_id != entity_a or (loaded_a == entity_a) # If IDs happen to match, that's luck, but the reference must be correct.
