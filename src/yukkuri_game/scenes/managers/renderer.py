"""
Gameplay Renderer Manager.
"""

from typing import TYPE_CHECKING, Any, Callable

from ...engine.event_bus import EventBus
from ...game.events import ResolutionChangedEvent

if TYPE_CHECKING:
    from ...scenes.gameplay import GameplayScene
    from ...engine.rendering.system import RenderingSystem
    from ...game.systems.day_night import DayNightSystem
    from ...game.ui.hud import HUD


class GameplayRenderer:
    """
    Manages rendering subsystems for the GameplayScene.
    """

    def __init__(self, scene: "GameplayScene", event_bus: EventBus) -> None:
        self.scene = scene
        self.event_bus = event_bus
        
        self.render_system: "RenderingSystem | None" = None
        self.day_night_system: "DayNightSystem | None" = None
        self.hud: "HUD | None" = None
        self._subscriptions: list[tuple[type[Any], Callable[[Any], None]]] = []

    def setup(self) -> None:
        """Sets up the rendering subsystems and event handlers."""
        # Setup event handlers
        self._subscribe(ResolutionChangedEvent, self._on_resolution_changed)

        if self.scene.application.headless:
            return

        from ...engine.rendering.system import RenderingSystem

        # Fetch RenderingSystem from world (registered via CoreRenderingPlugin)
        self.render_system = self.scene.world.services.try_get(RenderingSystem)
        
        # If it wasn't added by a plugin (unlikely but safe), create it
        if not self.render_system and self.scene.application.screen:
            from ...game.systems.rendering.passes import (
                create_gameplay_pipeline,
            )

            self.render_system = RenderingSystem(
                self.scene.application.screen,
                self.scene.world,
                pipeline=create_gameplay_pipeline(),
                lights_engine=getattr(
                    self.scene.application, "lights_engine", None
                ),
            )
            self.scene.world.services.register(
                self.render_system, RenderingSystem, replace=True
            )

        # Day/Night System
        try:
            from ...game.systems.day_night import DayNightSystem
            self.day_night_system = DayNightSystem()
            self.scene.world.add_system(self.day_night_system)
        except ImportError:
            self.day_night_system = None

        # HUD
        from ...game.ui.hud import HUD
        from ...config import GameConfig
        self.hud = HUD(self.scene.ui_manager, self.scene.world)
        self.hud.scene = self.scene

        # Honour debug_overlay_on_start setting from config.
        game_cfg = self.scene.world.services.try_get(GameConfig)
        if game_cfg and game_cfg.debug.debug_overlay_on_start:
            self.hud.toggle_debug()

        from ...game.ai.navigation_service import NavigationService
        nav_service = self.scene.world.services.try_get(NavigationService)
        if nav_service:
            self.hud.init_navigation_debug()
        self.hud.init_ai_debug()
        self.hud.init_physics_debug()
        
        # Link references back to the scene for legacy access
        self.scene.render_system = self.render_system
        self.scene.day_night_system = self.day_night_system
        self.scene.hud = self.hud

    def _subscribe(self, event_type: type[Any], handler: Callable[[Any], None]) -> None:
        self.event_bus.subscribe(event_type, handler)
        self._subscriptions.append((event_type, handler))

    def cleanup(self) -> None:
        for event_type, handler in self._subscriptions:
            self.event_bus.unsubscribe(event_type, handler)
        self._subscriptions.clear()
        if self.hud:
            self.hud.cleanup()
            self.hud = None
            self.scene.hud = None

    def _on_resolution_changed(self, event: ResolutionChangedEvent) -> None:
        if self.scene.application.headless:
            return

        self.scene.application.change_resolution(event.width, event.height, event.fullscreen)

        if self.render_system and self.scene.application.screen:
            from ...engine.rendering.system import RenderingSystem
            from ...game.systems.rendering.passes import (
                create_gameplay_pipeline,
            )

            self.render_system = RenderingSystem(
                self.scene.application.screen,
                self.scene.world,
                pipeline=create_gameplay_pipeline(),
                lights_engine=getattr(
                    self.scene.application, "lights_engine", None
                ),
            )
            self.scene.world.services.register(
                self.render_system, RenderingSystem, replace=True
            )
            self.scene.render_system = self.render_system
            if self.day_night_system:
                self.day_night_system.render_system = self.render_system

        self.scene.ui_manager.set_window_resolution((event.width, event.height))
        if self.hud:
            self.hud.resize(event.width, event.height)
        if hasattr(self.scene, "hud_surface"):
            del self.scene.hud_surface
            if hasattr(self.scene, "hud_texture"):
                del self.scene.hud_texture

    def update(self, dt: float) -> None:
        if self.scene.application.headless or not self.hud:
            return
        self.hud.fps_timer = getattr(self.hud, "fps_timer", 0.0) + dt
        if self.hud.fps_timer >= 0.25:
            clock: Any = self.scene.application.clock
            self.hud.fps = clock.get_fps()
            self.hud.fps_timer = 0.0
        self.hud.update(dt)

    def render(self, alpha: float) -> None:
        if self.render_system:
            self.render_system.render(self.scene.world, alpha)
        if not self.scene.application.headless and self.hud and self.scene.application.screen:
            self.hud.draw(self.scene.application.screen)
            self.scene.ui_manager.draw_ui(self.scene.application.screen)
