"""
Application Module.
"""

import gc
import os
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any

import pygame
import pygame_gui
from loguru import logger

from .audio import AudioManager
from .event_manager import EventManager, GamePhase
from .input_manager import InputManager
from .resource_manager import ResourceManager
from .scene_manager import SceneManager


class Application:
    """
    Main Application class responsible for the game loop, window, and scene management.
    """

    def __init__(
        self,
        width: int = 1280,
        height: int = 720,
        title: str = "Yukkuri Raising Game",
        headless: bool = False,
        render_scale: float = 1.0,
        deterministic: bool = False,
    ):
        """
        Initializes the application.

        Args:
            width: Window width in pixels.
            height: Window height in pixels.
            title: Application window title.
            headless: If True, runs without graphics (for tests/server).
            render_scale: Rendering resolution scale relative to window size.
            deterministic: If True, enforcing deterministic behavior (e.g., synchronous NavService, seeded RNG).
        """
        self.width = width
        self.height = height
        self.title = title
        self.headless = headless
        self.render_scale = render_scale
        self.deterministic = deterministic

        if self.deterministic:
            from .rng import seed

            seed(42)
            logger.info("Deterministic mode enabled. RNG seeded with 42.")

        self.lights_engine: Any = None
        self.screen: pygame.Surface | None = None

        if self.headless:
            os.environ["SDL_VIDEODRIVER"] = "dummy"

        pygame.init()

        self._initialize_display(width, height, fullscreen=False)

        self.clock = pygame.time.Clock()
        self.running = True

        self.resources = ResourceManager()
        self.resources.load_all_data()

        self.input_manager = InputManager()
        self.event_manager = EventManager()

        self.scene_manager = SceneManager()

        # Global UI Manager (for overlays or shared UI resources)
        self.ui_manager = pygame_gui.UIManager((width, height))

        # Surface for UI rendering
        self.ui_surface = pygame.Surface((width, height), pygame.SRCALPHA)

        self.fixed_dt = 1.0 / 60.0
        self.accumulator = 0.0

        logger.info("Application initialized.")

    def _initialize_display(
        self, width: int, height: int, fullscreen: bool = False
    ) -> None:
        """
        Initializes the display surface.

        Args:
            width: Width of the display.
            height: Height of the display.
            fullscreen: Whether to enable fullscreen mode.
        """
        self.lights_engine = None  # OpenGL backend currently disabled.

        if self.headless:
            self.screen = pygame.display.set_mode((width, height))
            logger.info("Headless mode: using software rendering (PygameBackend).")
        else:
            flags = pygame.FULLSCREEN if fullscreen else 0
            self.screen = pygame.display.set_mode((width, height), flags)
            pygame.display.set_caption(self.title)

    def change_resolution(
        self,
        width: int,
        height: int,
        fullscreen: bool,
        render_scale: float | None = None,
    ) -> None:
        """
        Changes the resolution and fullscreen state.

        Args:
            width: New width.
            height: New height.
            fullscreen: New fullscreen state.
            render_scale: Optional new render scale.
        """
        if render_scale is not None:
            self.render_scale = render_scale

        logger.info(
            f"Changing resolution to {width}x{height}, Fullscreen: {fullscreen}, Render Scale: {self.render_scale}"
        )
        self.width = width
        self.height = height

        # Re-initialize display (and LightingEngine)
        self._initialize_display(width, height, fullscreen)

        # Update UI Surface and Manager
        self.ui_surface = pygame.Surface((width, height), pygame.SRCALPHA)
        self.ui_manager.set_window_resolution((width, height))

    def run(self) -> None:
        """
        Starts the main game loop.

        Wraps the loop in a top-level exception handler that writes a
        timestamped crash log to ``logs/`` before re-raising so the
        process exits with a non-zero status code.
        """
        logger.info("Application Started")
        try:
            self._run_loop()
        except Exception:
            self._write_crash_log()
            raise

    def _run_loop(self) -> None:
        """
        Inner game loop body, separated so the crash handler can wrap it cleanly.
        """
        current_time = pygame.time.get_ticks() / 1000.0

        while self.running:
            new_time = pygame.time.get_ticks() / 1000.0
            frame_time = new_time - current_time
            current_time = new_time

            if frame_time > 0.25:
                frame_time = 0.25
            self.accumulator += frame_time

            # Input processing should happen every frame
            self.process_events()

            while self.accumulator >= self.fixed_dt:
                self.update(self.fixed_dt)
                self.accumulator -= self.fixed_dt

            if not self.headless:
                self.render()
                self.clock.tick(60)
            else:
                self.clock.tick(60)

        self.quit()

    def _write_crash_log(self) -> None:
        """
        Writes a crash log containing the full traceback and world state.

        The log is written to ``logs/crash_YYYYMMDD_HHMMSS.log``.
        A short human-readable notice is also printed to stderr.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_dir = Path("logs")
        log_dir.mkdir(parents=True, exist_ok=True)
        crash_path = log_dir / f"crash_{timestamp}.log"

        tb_text = traceback.format_exc()

        # Active scene name for the header.
        scene = self.scene_manager.current_scene
        scene_name = (
            type(scene).__name__ if scene is not None else "<no scene>"
        )
        scene_stack = self.scene_manager.dump_scene_stack()

        lines: list[str] = [
            f"=== CRASH REPORT {timestamp} ===",
            f"Scene: {scene_name}  |  Stack: {scene_stack}",
            "",
            "--- Traceback ---",
            tb_text,
        ]

        _, exc_value, _ = sys.exc_info()
        from .exceptions import GameEngineError  # noqa: PLC0415
        if isinstance(exc_value, GameEngineError) and exc_value.context:
            lines.append("--- Exception Context ---")
            for k, v in exc_value.context.items():
                lines.append(f"  {k}: {v}")
            lines.append("")

        # Dump the last 100 published event names from the active world's bus.
        try:
            if scene is not None and hasattr(scene, "world"):
                world = scene.world  # type: ignore[union-attr]
                from .event_bus import EventBus  # noqa: PLC0415
                bus = world.services.try_get(EventBus)
                if bus and bus.recent_events:
                    lines.append("--- Recent Events (last 100) ---")
                    for ev in bus.recent_events:
                        if isinstance(ev, dict):
                            ts = datetime.fromtimestamp(
                                ev["timestamp"]
                            ).strftime("%H:%M:%S.%f")[:-3]
                            lines.append(
                                f"  [{ts}] {ev['type']}{ev['payload']}"
                            )
                        else:
                            lines.append(f"  {ev}")
                    lines.append("")
        except Exception as ev_err:  # noqa: BLE001
            lines.append(f"[Event history unavailable: {ev_err}]")

        # Attempt to dump world state from the active scene.
        try:
            if scene is not None and hasattr(scene, "world"):
                import dataclasses  # noqa: PLC0415

                world = scene.world  # type: ignore[union-attr]
                lines.append("--- World State ---")
                for entity in world.get_all_entities():
                    comps = world.get_all_components(entity)
                    comp_strs: list[str] = []
                    for c in comps:
                        if dataclasses.is_dataclass(c):
                            try:
                                flds = dataclasses.fields(c)
                                kv = []
                                for f in flds:
                                    try:
                                        kv.append(
                                            f"{f.name}="
                                            f"{getattr(c, f.name)!r}"
                                        )
                                    except Exception:  # noqa: BLE001
                                        kv.append(f"{f.name}=<err>")
                                comp_strs.append(
                                    f"{type(c).__name__}"
                                    f"({', '.join(kv)})"
                                )
                            except Exception:  # noqa: BLE001
                                comp_strs.append(type(c).__name__)
                        else:
                            comp_strs.append(type(c).__name__)
                    lines.append(
                        f"  Entity {entity}: {comp_strs}"
                    )
        except Exception as dump_err:  # noqa: BLE001
            lines.append(f"[World dump failed: {dump_err}]")


        crash_text = "\n".join(lines)

        try:
            crash_path.write_text(crash_text, encoding="utf-8")
        except OSError as write_err:
            logger.error(f"Could not write crash log: {write_err}")
            return

        # Attempt to capture a screenshot at crash time.
        if self.screen is not None:
            screenshot_path = log_dir / f"crash_{timestamp}.png"
            try:
                pygame.image.save(self.screen, str(screenshot_path))
                logger.critical(
                    "Crash screenshot saved to: {}",
                    screenshot_path.resolve(),
                )
            except Exception as ss_err:  # noqa: BLE001
                logger.warning(
                    "Could not save crash screenshot: {}", ss_err
                )

        logger.critical(
            f"Game crashed — crash log saved to: {crash_path.resolve()}"
        )
        print(
            f"\n[CRASH] The game crashed unexpectedly."
            f"\nCrash log saved to: {crash_path.resolve()}"
            f"\nPlease include this file when reporting bugs.",
            file=sys.stderr,
        )

    def process_events(self) -> None:
        """
        Process input events from the system queue.

        Delegates to InputManager, UIManager, and SceneManager.
        """
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

            self.input_manager.process_event(event)
            self.ui_manager.process_events(event)
            self.scene_manager.handle_event(event)

    def update(self, dt: float) -> None:
        """
        Update application logic and systems.

        Args:
            dt: Delta time in seconds.
        """
        # 1. Pre-Update Phase (Prepare systems)
        self.event_manager.process_phase(GamePhase.PRE_UPDATE)

        # 2. Main Game Logic
        self.ui_manager.update(dt)
        self.scene_manager.update(dt)

        # 3. Update Phase (Systems responding to frame logic)
        self.event_manager.process_phase(GamePhase.UPDATE)

        # 4. Post-Update (Cleanup)
        self.event_manager.process_phase(GamePhase.POST_UPDATE)

        # 5. Update Input State (Clear transient state)
        self.input_manager.update()

    def render(self) -> None:
        """
        Render the application frame.
        """
        # Ensure screen is available (mypy check)
        if self.screen is None:
            return

        # Render
        if not self.headless:
            # Calculate interpolation factor (alpha)
            # alpha = accumulator / fixed_dt
            # This represents how far we are between the previous physics step and the next one.
            alpha = 0.0
            if self.fixed_dt > 0:
                alpha = self.accumulator / self.fixed_dt
                # Clamp alpha to [0.0, 1.0] to prevent extrapolation artifacts
                alpha = max(0.0, min(1.0, alpha))

            self.screen.fill((0, 0, 0))
            self.scene_manager.render(alpha)
            self.ui_manager.draw_ui(self.screen)
            pygame.display.flip()

    def init_render_system_headless(self) -> None:
        """
        Initializes the render system for the current scene if in headless mode.

        This allows taking screenshots or verifying rendering logic without a window.
        """
        if self.scene_manager.current_scene and hasattr(
            self.scene_manager.current_scene, "init_render_system_headless"
        ):
            scene: Any = self.scene_manager.current_scene
            getattr(scene, "init_render_system_headless", lambda: None)()

    def quit(self) -> None:
        """
        Stops the application and cleans up resources.
        """
        logger.info("Application Ended")
        if self.scene_manager:
            while self.scene_manager.current_scene:  # Pop all scenes for cleanup.
                self.scene_manager.pop()

        # Use getattr to avoid static attribute access issues if `audio` was never set.
        audio = getattr(self, "audio", None)
        if isinstance(audio, AudioManager):
            audio.clear()

        if self.resources:
            self.resources.clear()

        if self.running:
            self.running = False
        pygame.quit()

        # Final GC
        gc.collect()
