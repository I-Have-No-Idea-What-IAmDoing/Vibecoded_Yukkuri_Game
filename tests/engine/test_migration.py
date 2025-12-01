import pytest
from typing import Dict, Any
from yukkuri_game.engine.migration import MigrationRegistry

def test_migration_registration():
    """Test that migrations can be registered."""

    class TestComponent:
        pass

    def migrate_v1_v2(data: Dict[str, Any]) -> Dict[str, Any]:
        data['new_field'] = 'migrated'
        return data

    MigrationRegistry.register(TestComponent, 1, 2, migrate_v1_v2)

    assert "TestComponent" in MigrationRegistry._migrations
    migrations = MigrationRegistry._migrations["TestComponent"]
    assert len(migrations) > 0
    assert migrations[-1][0] == 1
    assert migrations[-1][1] == 2
    assert migrations[-1][2] == migrate_v1_v2

@pytest.fixture(autouse=True)
def clear_registry():
    old_migrations = MigrationRegistry._migrations.copy()
    MigrationRegistry._migrations = {}
    yield
    MigrationRegistry._migrations = old_migrations

def test_migration_execution():
    """Test that migrations are executed correctly."""

    class MockComponent:
        pass

    def v1_to_v2(data: Dict[str, Any]) -> Dict[str, Any]:
        data['v'] = 2
        data['field_v2'] = 'added'
        return data

    def v2_to_v3(data: Dict[str, Any]) -> Dict[str, Any]:
        data['v'] = 3
        data['field_v3'] = 'added_more'
        return data

    MigrationRegistry.register(MockComponent, 1, 2, v1_to_v2)
    MigrationRegistry.register(MockComponent, 2, 3, v2_to_v3)

    initial_data = {'v': 1, 'original': True}

    # Migrate 1 -> 3
    migrated_data = MigrationRegistry.migrate(
        "MockComponent",
        initial_data.copy(),
        current_version=1,
        target_version=3
    )

    assert migrated_data['v'] == 3
    assert migrated_data['original'] is True
    assert migrated_data['field_v2'] == 'added'
    assert migrated_data['field_v3'] == 'added_more'

def test_migration_not_needed():
    """Test that migration is skipped if versions match or target is lower."""
    class MockComponent:
        pass

    data = {'v': 2}
    result = MigrationRegistry.migrate("MockComponent", data, 2, 2)
    assert result is data

    result = MigrationRegistry.migrate("MockComponent", data, 2, 1)
    assert result is data

def test_migration_partial():
    """Test partial migration when not all steps are available."""
    class MockComponent:
        pass

    def v1_to_v2(data):
        data['v'] = 2
        return data

    MigrationRegistry.register(MockComponent, 1, 2, v1_to_v2)

    initial_data = {'v': 1}
    # Target 3, but only have path to 2
    migrated_data = MigrationRegistry.migrate("MockComponent", initial_data.copy(), 1, 3)

    assert migrated_data['v'] == 2

def test_migration_no_registry_entry():
    """Test behavior when component has no migrations registered."""
    data = {'v': 1}
    result = MigrationRegistry.migrate("UnknownComponent", data, 1, 2)
    assert result is data
