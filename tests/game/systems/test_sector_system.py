
import pytest
from unittest.mock import MagicMock
from yukkuri_game.game.systems.sector_system import SectorSystem
from yukkuri_game.game.components import Transform
from yukkuri_game.engine.ecs import World

class TestSectorSystemOptimization:
    def test_optimization_logic(self):
        """Test that SectorSystem correctly optimizes updates."""
        world = World()
        sector_system = SectorSystem(width=1000, height=1000, sector_size=100)
        # Manually register the map since system does it in update usually
        world.services.register(sector_system.sector_map, type(sector_system.sector_map))

        # 1. New Entity
        entity = world.create_entity(Transform(x=50, y=50))
        transform = world.get_component(entity, Transform)

        # Mock update_entity to track calls
        sector_system.sector_map.update_entity = MagicMock(wraps=sector_system.sector_map.update_entity)

        # Run update
        sector_system.update(world, 0.1)

        # Should be called because it's new (not in entity_sectors)
        sector_system.sector_map.update_entity.assert_called_with(entity, 50, 50)
        assert entity in sector_system.sector_map.entity_sectors

        # Reset mock
        sector_system.sector_map.update_entity.reset_mock()

        # 2. Static Entity (No movement)
        sector_system.update(world, 0.1)

        # Should NOT be called (optimized away)
        sector_system.sector_map.update_entity.assert_not_called()

        # 3. Moved Entity
        transform.x = 60
        # NOTE: prev_x is NOT automatically updated by Transform. It's updated by PhysicsSystem usually.
        # But SectorSystem compares x vs prev_x.
        # If we only update x, then x != prev_x (50).

        sector_system.update(world, 0.1)

        # Should be called
        sector_system.sector_map.update_entity.assert_called_with(entity, 60, 50)

        # Manually sync prev_x to simulate PhysicsSystem end-of-frame
        transform.prev_x = 60
        transform.prev_y = 50

        sector_system.sector_map.update_entity.reset_mock()

        # 4. Static again
        sector_system.update(world, 0.1)
        sector_system.sector_map.update_entity.assert_not_called()

    def test_occluder_optimization(self):
        """Test OccluderMap optimization."""
        from yukkuri_game.game.components import Occluder

        world = World()
        sector_system = SectorSystem(width=1000, height=1000, sector_size=100)

        entity = world.create_entity(Transform(x=50, y=50), Occluder())
        transform = world.get_component(entity, Transform)

        sector_system.occluder_map.update_entity = MagicMock(wraps=sector_system.occluder_map.update_entity)

        # 1. New
        sector_system.update(world, 0.1)
        sector_system.occluder_map.update_entity.assert_called_with(entity, 50, 50)

        sector_system.occluder_map.update_entity.reset_mock()

        # 2. Static
        sector_system.update(world, 0.1)
        sector_system.occluder_map.update_entity.assert_not_called()

        # 3. Moved
        transform.x = 60
        sector_system.update(world, 0.1)
        sector_system.occluder_map.update_entity.assert_called_with(entity, 60, 50)

if __name__ == "__main__":
    pytest.main([__file__])
