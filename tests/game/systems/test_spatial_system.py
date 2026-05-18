
import pytest
from unittest.mock import MagicMock
from yukkuri_game.game.systems.spatial_system import SpatialSystem
from yukkuri_game.game.components import Transform, Velocity
from yukkuri_game.engine.ecs import World
from yukkuri_game.engine.event_bus import EventBus

class TestSpatialSystemOptimization:
    def test_optimization_logic(self):
        """Test that SpatialSystem correctly optimizes updates."""
        world = World()
        # Register EventBus to enable optimization mode
        event_bus = EventBus()
        world.services.register(event_bus, EventBus)

        spatial_system = SpatialSystem(width=1000, height=1000, sector_size=100)
        world.add_system(spatial_system) # Initializes system properly

        # Services are now registered automatically by add_system() -> initialize()

        # 1. New Entity
        entity = world.create_entity(Transform(x=50, y=50))
        transform = world.get_component(entity, Transform)

        # Mock update_entity to track calls
        spatial_system.spatial_service.update_entity = MagicMock(wraps=spatial_system.spatial_service.update_entity)

        # Run update
        spatial_system.update(world, 0.1)

        # Should be called because it's new (not in entity_sectors)
        spatial_system.spatial_service.update_entity.assert_called_with(entity, 50, 50)
        assert entity in spatial_system.spatial_service.entity_sectors

        # Reset mock
        spatial_system.spatial_service.update_entity.reset_mock()

        # 2. Static Entity (No movement)
        spatial_system.update(world, 0.1)

        # Should NOT be called (optimized away)
        spatial_system.spatial_service.update_entity.assert_not_called()

        # 3. Moved Entity
        transform.x = 60
        # Optimization logic requires entity to be dynamic (have Velocity/PhysicsBody etc)
        # Add Velocity component to simulate dynamic entity
        world.add_component(entity, Velocity(dx=10, dy=0))

        # NOTE: prev_x is NOT automatically updated by Transform. It's updated by PhysicsSystem usually.
        # But SpatialSystem compares x vs prev_x.
        # If we only update x, then x != prev_x (50).

        spatial_system.update(world, 0.1)

        # Should be called
        spatial_system.spatial_service.update_entity.assert_called_with(entity, 60, 50)

        # Manually sync prev_x to simulate PhysicsSystem end-of-frame
        transform.prev_x = 60
        transform.prev_y = 50

        spatial_system.spatial_service.update_entity.reset_mock()

        # 4. Static again
        spatial_system.update(world, 0.1)
        spatial_system.spatial_service.update_entity.assert_not_called()

    def test_occluder_optimization(self):
        """Test OccluderMap optimization."""
        from yukkuri_game.game.components import Occluder

        world = World()
        # Register EventBus to enable optimization mode
        event_bus = EventBus()
        world.services.register(event_bus, EventBus)

        spatial_system = SpatialSystem(width=1000, height=1000, sector_size=100)
        world.add_system(spatial_system)

        entity = world.create_entity(Transform(x=50, y=50), Occluder())
        transform = world.get_component(entity, Transform)

        spatial_system.occluder_map.update_entity = MagicMock(wraps=spatial_system.occluder_map.update_entity)

        # 1. New
        spatial_system.update(world, 0.1)
        spatial_system.occluder_map.update_entity.assert_called_with(entity, 50, 50)

        spatial_system.occluder_map.update_entity.reset_mock()

        # 2. Static
        spatial_system.update(world, 0.1)
        spatial_system.occluder_map.update_entity.assert_not_called()

        # 3. Moved
        transform.x = 60
        # Add dynamic component to ensure update
        world.add_component(entity, Velocity(dx=10, dy=0))

        spatial_system.update(world, 0.1)
        spatial_system.occluder_map.update_entity.assert_called_with(entity, 60, 50)

        # Manually sync prev_x to simulate PhysicsSystem end-of-frame
        transform.prev_x = transform.x
        transform.prev_y = transform.y

        spatial_system.occluder_map.update_entity.reset_mock()

        # 4. Static again
        spatial_system.update(world, 0.1)
        spatial_system.occluder_map.update_entity.assert_not_called()

if __name__ == "__main__":
    pytest.main([__file__])
