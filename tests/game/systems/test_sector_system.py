
import pytest
from unittest.mock import Mock, MagicMock
from yukkuri_game.engine.ecs import World
from yukkuri_game.engine.events import EntityDestroyedEvent
from yukkuri_game.game.systems.sector_system import SectorSystem, SectorMap, OccluderMap
from yukkuri_game.game.components import Transform, Occluder

class TestSectorMap:
    @pytest.fixture
    def sector_map(self):
        return SectorMap(width=1000, height=1000, sector_size=100)

    def test_get_sector_coords(self, sector_map):
        assert sector_map.get_sector_coords(0, 0) == (0, 0)
        assert sector_map.get_sector_coords(150, 150) == (1, 1)
        assert sector_map.get_sector_coords(950, 950) == (9, 9)
        # Check clamping
        assert sector_map.get_sector_coords(-100, -100) == (0, 0)
        assert sector_map.get_sector_coords(2000, 2000) == (9, 9)

    def test_update_entity(self, sector_map):
        entity_id = 1
        sector_map.update_entity(entity_id, 50, 50)
        assert sector_map.entity_sectors[entity_id] == (0, 0)
        assert entity_id in sector_map.sectors[(0, 0)]

        # Move to new sector
        sector_map.update_entity(entity_id, 150, 150)
        assert sector_map.entity_sectors[entity_id] == (1, 1)
        assert entity_id in sector_map.sectors[(1, 1)]
        assert entity_id not in sector_map.sectors[(0, 0)]

        # Move within same sector
        sector_map.update_entity(entity_id, 160, 160)
        assert sector_map.entity_sectors[entity_id] == (1, 1)

    def test_remove_entity(self, sector_map):
        entity_id = 1
        sector_map.update_entity(entity_id, 50, 50)
        sector_map.remove_entity(entity_id)
        
        assert entity_id not in sector_map.entity_sectors
        assert entity_id not in sector_map.sectors[(0, 0)]

    def test_get_entities_in_sector(self, sector_map):
        sector_map.update_entity(1, 50, 50)
        sector_map.update_entity(2, 50, 50)
        sector_map.update_entity(3, 150, 150)

        entities = sector_map.get_entities_in_sector(0, 0)
        assert 1 in entities
        assert 2 in entities
        assert 3 not in entities

    def test_get_adjacent_sectors(self, sector_map):
        # Corner case
        adj = sector_map.get_adjacent_sectors(0, 0)
        assert (0, 1) in adj
        assert (1, 0) in adj
        assert (1, 1) in adj
        assert len(adj) == 3

        # Middle case
        adj = sector_map.get_adjacent_sectors(1, 1)
        assert len(adj) == 8 # All 8 neighbors

    def test_get_entities_in_range(self, sector_map):
        # 1 at (0,0), 2 at (100,0) [neighbor], 3 at (200,0) [far]
        sector_map.update_entity(1, 50, 50) # Sector 0,0
        sector_map.update_entity(2, 150, 50) # Sector 1,0
        sector_map.update_entity(3, 250, 50) # Sector 2,0

        # Visual (Same + Adjacent)
        visual = sector_map.get_entities_in_range(50, 50, "visual")
        assert 1 in visual
        assert 2 in visual
        assert 3 not in visual

        # Auditory Loud (Same + Adjacent)
        loud = sector_map.get_entities_in_range(50, 50, "auditory_loud")
        assert 1 in loud
        assert 2 in loud
        assert 3 not in loud

        # Auditory (Same only - Wait, code implementation check)
        # Look at implementation:
        # if range_type in ["visual", "auditory_loud"]: include adjacent
        # default is only same sector
        quiet = sector_map.get_entities_in_range(50, 50, "auditory")
        assert 1 in quiet
        assert 2 not in quiet # Adjacent not included for basic auditory
        assert 3 not in quiet

    def test_get_entities_in_radius(self, sector_map):
        sector_map.update_entity(1, 50, 50)
        
        # Radius 60 covers (50,50)
        entities = sector_map.get_entities_in_radius(50, 50, 60)
        assert 1 in entities

        # Radius too small to touch check depends on implementation which is sector based
        # Implementation gets all sectors touching bounds
        # If radius is small but still inside sector 0,0, it returns entities in 00
        
    def test_get_entities_in_rect(self, sector_map):
        sector_map.update_entity(1, 50, 50)
        
        entities = sector_map.get_entities_in_rect(0, 0, 100, 100)
        assert 1 in entities
        
        entities = sector_map.get_entities_in_rect(200, 200, 50, 50)
        assert 1 not in entities


class TestSectorSystem:
    @pytest.fixture
    def world(self):
        return World()

    @pytest.fixture
    def system(self, world):
        sys = SectorSystem(width=1000, height=1000, sector_size=100)
        return sys

    def test_initialization(self, system):
        assert isinstance(system.sector_map, SectorMap)
        assert isinstance(system.occluder_map, OccluderMap)

    def test_update_registers_services(self, world, system):
        system.update(world, 0.1)
        assert world.services.try_get(SectorMap) == system.sector_map
        assert world.services.try_get(OccluderMap) == system.occluder_map

    def test_update_syncs_transforms(self, world, system):
        system.update(world, 0.1) # Register services
        
        entity = world.create_entity()
        world.add_component(entity, Transform(x=50, y=50))
        
        system.update(world, 0.1)
        
        assert system.sector_map.entity_sectors[entity] == (0, 0)
        
        # Move entity
        world.get_component(entity, Transform).x = 150
        world.get_component(entity, Transform).y = 150
        
        system.update(world, 0.1)
        assert system.sector_map.entity_sectors[entity] == (1, 1)

    def test_update_syncs_occluders(self, world, system):
        system.update(world, 0.1)
        
        entity = world.create_entity()
        world.add_component(entity, Transform(x=50, y=50))
        world.add_component(entity, Occluder())
        
        system.update(world, 0.1)
        
        assert system.occluder_map.entity_sectors[entity] == (0, 0)

    def test_entity_destroyed_handler(self, world, system):
        # Mock event bus
        event_bus = Mock()
        system.event_bus = event_bus
        
        entity = 1
        system.sector_map.update_entity(entity, 50, 50)
        system.occluder_map.update_entity(entity, 50, 50)
        
        event = EntityDestroyedEvent(entity_id=entity)
        system.on_entity_destroyed(event)
        
        assert entity not in system.sector_map.entity_sectors
        assert entity not in system.occluder_map.entity_sectors

    def test_cleanup_dead_entities(self, world, system):
        system.update(world, 0.1)
        
        # Create entity and register it
        entity = world.create_entity()
        world.add_component(entity, Transform(x=50, y=50))
        system.update(world, 0.1)
        
        assert entity in system.sector_map.entity_sectors
        
        # Remove Transform
        world.remove_component(entity, Transform)
        
        # Trigger cleanup
        system.cleanup_timer = system.cleanup_interval + 1
        system.update(world, 0.1)
        
        assert entity not in system.sector_map.entity_sectors
