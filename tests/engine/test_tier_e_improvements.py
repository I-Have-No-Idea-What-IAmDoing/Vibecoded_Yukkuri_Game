"""Tests for Tier E debugging improvements."""

import contextlib
import dataclasses
import io
import json
import os
import sqlite3
import sys
from typing import Any
from unittest.mock import MagicMock
from unittest.mock import patch

import msgspec
import pygame
import pymunk
import pytest

from scripts.inspect_save import main as inspect_save_main
from yukkuri_game.engine.components import PhysicsBody
from yukkuri_game.engine.components import Transform
from yukkuri_game.engine.event_bus import Event
from yukkuri_game.engine.event_bus import EventBus
from yukkuri_game.engine.event_manager import GamePhase
from yukkuri_game.game.systems import physics_debug_renderer
from yukkuri_game.scenes.gameplay import GameplayScene
from yukkuri_game.testing.driver import GameDriver


def test_save_file_inspector(tmp_path: Any) -> None:
    """Verifies that inspect_save.py parses SQLite and msgpack data.

    Args:
        tmp_path (Any): The temporary path fixture from pytest.
    """
    db_path = os.path.join(tmp_path, "test_save.sqlite")

    # Create dummy SQLite save database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "CREATE TABLE global_state (key TEXT PRIMARY KEY, value TEXT)"
    )
    cursor.execute(
        "INSERT INTO global_state (key, value) VALUES (?, ?)",
        ("global_data", '{"money": 1000, "time": 12.3}'),
    )
    cursor.execute("CREATE TABLE chunks (chunk_id TEXT PRIMARY KEY, data BLOB)")

    # Msgpack entities payload
    entities = [
        {
            "entity_id": 1,
            "stable_id": 10,
            "components": {
                "Transform": {"x": 100.0, "y": 200.0},
                "Needs": {"health": 90.0},
            },
        },
        {
            "entity_id": 2,
            "stable_id": 20,
            "components": {"Transform": {"x": 300.0, "y": 400.0}},
        },
    ]
    blob = msgspec.msgpack.encode(entities)
    cursor.execute(
        "INSERT INTO chunks (chunk_id, data) VALUES (?, ?)",
        ("0_0", blob),
    )
    conn.commit()
    conn.close()

    # 1. Test full JSON output
    stdout_buf = io.StringIO()
    with (
        patch.object(sys, "argv", ["inspect_save.py", db_path]),
        contextlib.redirect_stdout(stdout_buf),
    ):
        inspect_save_main()

    out_json = json.loads(stdout_buf.getvalue())
    assert out_json["global_data"]["money"] == 1000
    assert "0_0" in out_json["chunks"]
    assert out_json["chunks"]["0_0"][0]["entity_id"] == 1

    # 2. Test summary output
    stdout_buf = io.StringIO()
    with (
        patch.object(
            sys, "argv", ["inspect_save.py", db_path, "--summary"]
        ),
        contextlib.redirect_stdout(stdout_buf),
    ):
        inspect_save_main()

    summary_text = stdout_buf.getvalue()
    assert "Total Chunks: 1" in summary_text
    assert "Total Matched Entities: 2" in summary_text
    assert "money: 1000" in summary_text

    # 3. Test entity filtering
    stdout_buf = io.StringIO()
    with (
        patch.object(
            sys, "argv", ["inspect_save.py", db_path, "--entity", "2"]
        ),
        contextlib.redirect_stdout(stdout_buf),
    ):
        inspect_save_main()

    out_json = json.loads(stdout_buf.getvalue())
    assert len(out_json["chunks"]["0_0"]) == 1
    assert out_json["chunks"]["0_0"][0]["entity_id"] == 2


def test_physics_debug_renderer(game_driver: GameDriver) -> None:
    """Verifies that PhysicsDebugRenderer draws active bodies.

    Args:
        game_driver (GameDriver): The game driver fixture.
    """
    driver = game_driver
    driver.setup()

    # Create dummy entity with PhysicsBody and Transform
    y = driver.world.create_entity()
    trans = Transform(x=100.0, y=200.0)
    driver.world.add_component(y, trans)

    body = pymunk.Body(1.0, 1.0)
    body.position = pymunk.vec2d.Vec2d(100.0, 200.0)
    shape = pymunk.Circle(body, 10.0)
    pbody = PhysicsBody(body=body, shape=shape)
    driver.world.add_component(y, pbody)

    renderer = physics_debug_renderer.PhysicsDebugRenderer(driver.world)
    renderer.toggle()
    assert renderer.enabled is True

    # Render on mock surface
    surface = pygame.Surface((800, 600))
    with patch("pygame.draw.circle") as mock_circle:
        renderer.render(surface, driver.world)
        mock_circle.assert_called_once()


def test_event_replay_payload_buffer() -> None:
    """Verifies that EventBus records full payloads in recent_events."""
    bus = EventBus()
    bus.trace = True

    @dataclasses.dataclass(frozen=True)
    class DummyEvent(Event):
        name: str
        val: int

    event = DummyEvent(name="TestEvent", val=42)
    bus.publish(event)

    assert len(bus.recent_events) == 1
    record = bus.recent_events[0]
    assert record["type"] == "DummyEvent"
    assert "name='TestEvent'" in record["payload"]
    assert "val=42" in record["payload"]


def test_pause_stepping() -> None:
    """Verifies that step-framing advances gameplay scene by one tick."""
    # Mock Application
    app = MagicMock()
    app.headless = True
    app.width = 1280
    app.height = 720

    with patch("pygame_gui.UIManager"):
        scene = GameplayScene(app)

    # Mock session_manager and event_manager to see if it sets _step_frame_requested
    session = MagicMock()
    session.paused = True
    setattr(session, "_step_frame_requested", True)
    scene.session_manager = session

    scene.event_manager = MagicMock()
    scene.world = MagicMock()
    scene.camera = MagicMock()
    scene.renderer_manager = MagicMock()

    scene.update(0.016)

    # Asserts that GamePhase.UPDATE was processed because step_requested was True
    scene.event_manager.process_phase.assert_any_call(GamePhase.UPDATE)
    # Asserts that step_requested was reset to False
    assert getattr(session, "_step_frame_requested") is False
