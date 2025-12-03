import pytest
from unittest.mock import Mock, MagicMock
from yukkuri_game.engine.scene_manager import SceneManager, Scene, SceneContext
from yukkuri_game.engine.migration import MigrationRegistry
import msgspec
import os

class MockScene(Scene):
    def __init__(self, application=None):
        if application is None:
            application = MagicMock()
        super().__init__(application)
        self.setup_called = False
        self.enter_called = False
        self.exit_called = False
        self.update_called = False
        self.render_called = False
        self.handle_event_called = False

    def setup(self, context: SceneContext) -> None:
        self.setup_called = True
        self.context = context

    def on_enter(self) -> None:
        self.enter_called = True

    def on_exit(self) -> None:
        self.exit_called = True

    def update(self, dt: float) -> None:
        self.update_called = True

    def render(self) -> None:
        self.render_called = True

    def handle_event(self, event) -> None:
        self.handle_event_called = True

class SceneWithInjection(MockScene):
    INJECTIONS = {"test_data": int}

class SceneWithStructInjection(MockScene):
    pass

from typing import ClassVar

class MyStruct(msgspec.Struct):
    value: int
    _version_: ClassVar[int] = 1

SceneWithStructInjection.INJECTIONS = {"my_struct": MyStruct}

@pytest.fixture(autouse=True)
def clear_registry():
    old_migrations = MigrationRegistry._migrations.copy()
    MigrationRegistry._migrations = {}
    yield
    MigrationRegistry._migrations = old_migrations

def test_scene_stack_operations():
    sm = SceneManager()
    scene1 = MockScene()
    scene2 = MockScene()

    # Test Push
    sm.push(scene1)
    assert sm.current_scene == scene1
    assert scene1.setup_called
    assert scene1.enter_called

    # Test Push another
    sm.push(scene2)
    assert sm.current_scene == scene2
    assert scene2.setup_called
    assert scene2.enter_called

    # Test Pop
    sm.pop()
    assert sm.current_scene == scene1
    assert scene2.exit_called

    # Test Replace
    scene3 = MockScene()
    sm.replace(scene3)
    assert sm.current_scene == scene3
    assert scene1.exit_called
    assert scene3.enter_called

def test_delegation():
    sm = SceneManager()
    scene = MockScene()
    sm.push(scene)

    sm.update(0.1)
    assert scene.update_called

    sm.render()
    assert scene.render_called

    event = MagicMock()
    sm.handle_event(event)
    assert scene.handle_event_called

def test_global_data_persistence(tmp_path):
    sm = SceneManager()
    sm.set_global_data("score", 100)
    assert sm.get_global_data("score") == 100

    file_path = tmp_path / "global.dat"
    sm.save_global_data(str(file_path))

    sm2 = SceneManager()
    sm2.load_global_data(str(file_path))
    assert sm2.get_global_data("score") == 100

def test_injection_simple():
    sm = SceneManager()
    sm.set_global_data("test_data", 42)

    scene = SceneWithInjection()
    sm.push(scene)

    assert scene.context.data["test_data"] == 42

def test_injection_hydration_and_migration():
    """Test hydrating a dict into a Struct and applying migration."""
    sm = SceneManager()

    # Simulate data loaded from file (dict) with old version
    raw_data = {"value": 10, "_version_": 0}
    sm.set_global_data("my_struct", raw_data)

    # Register migration
    def migrate_0_to_1(data):
        data["value"] += 5
        return data

    MigrationRegistry.register(MyStruct, 0, 1, migrate_0_to_1)

    scene = SceneWithStructInjection()
    sm.push(scene)

    injected = scene.context.data["my_struct"]
    assert isinstance(injected, MyStruct)
    assert injected.value == 15  # 10 + 5

    # Also verify it updated the persistent data in memory to the object
    assert isinstance(sm.get_global_data("my_struct"), MyStruct)
