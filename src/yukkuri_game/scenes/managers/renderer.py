"""
Gameplay Renderer Manager.

Abstracts the initialization and rendering of RenderingSystem,
DayNightSystem, and HUD.
"""

from typing import TYPE_CHECKING, Any, Callable

from ...engine.event_bus import EventBus
from ...game.events import ResolutionChangedEvent

if TYPE_CHECKING:
    from ...scenes.gameplay import GameplayScene
    from ...game.systems.rendering.system import RenderingSystem
    from ...game.systems.day_night import DayNightSystem
    from ...game.ui.hud import HUD


class GameplayRenderer:
    """
    Manages rendering subsystems for the GameplayScene.

    Attributes:
        scene (GameplayScene): The owning scene.
        event_bus (EventBus): The active event bus.
        render_system (RenderingSystem | None): The rendering system.
        day_night_system (DayNightSystem | None): The day/night system.
        hud (HUD | None): The Heads-Up Display manager.
        _subscriptions (list[tuple[type, Callable]]): Tracked subscriptions for cleanup.
    """

    def __init__(self, scene: "GameplayScene", event_bus: EventBus) -> None:
        """
        Initializes the renderer manager.

        Args:
            scene (GameplayScene): The owning scene.
            event_bus (EventBus): The global event bus.
        """
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

        if self.scene.application.headless or not self.scene.application.screen:
            return

        from ...game.systems.rendering.system import RenderingSystem

        self.render_system = RenderingSystem(
            self.scene.application.screen,
            self.scene.world,
            lights_engine=getattr(self.scene.application, "lights_engine", None),
        )
        self.scene.world.services.register(self.render_system, RenderingSystem)

        # Day/Night System
        try:
            from ...game.systems.day_night import DayNightSystem
        except ImportError:
            DayNightSystem = None  # type: ignore

        if DayNightSystem is not None:
            self.day_night_system = DayNightSystem()
            self.scene.world.add_system(self.day_night_system)

        # HUD
        from ...game.ui.hud import HUD
        self.hud = HUD(self.scene.ui_manager, self.scene.world)

        # Initialize navigation debug renderer
        from ...game.ai.navigation_service import NavigationService
        nav_service = self.scene.world.services.try_get(NavigationService)
        if nav_service:
            self.hud.init_navigation_debug()

        # Initialize AI Debug
        self.hud.init_ai_debug()
        
        # Link references back to the scene for legacy access
        self.scene.render_system = self.render_system
        self.scene.day_night_system = self.day_night_system
        self.scene.hud = self.hud

    def _subscribe(self, event_type: type[Any], handler: Callable[[Any], None]) -> None:
        """Subscribes a handler and tracks it for cleanup."""
        self.event_bus.subscribe(event_type, handler)
        self._subscriptions.append((event_type, handler))

    def cleanup(self) -> None:
        """Cleans up resources and event handlers."""
        for event_type, handler in self._subscriptions:
            self.event_bus.unsubscribe(event_type, handler)
        self._subscriptions.clear()

        if self.hud:
            self.hud.cleanup()
            self.hud = None
            self.scene.hud = None

    def _on_resolution_changed(self, event: ResolutionChangedEvent) -> None:
        """
        Handles resolution change event.

        Args:
            event (ResolutionChangedEvent): The event data.
        """
        if self.scene.application.headless:
            return

        # Delegate resolution change to Application which handles LightingEngine lifecycle
        self.scene.application.change_resolution(event.width, event.height, event.fullscreen)

        # Re-initialize RenderSystem to use the new LightingEngine instance
        if self.render_system and self.scene.application.screen:
            from ...game.systems.rendering.system import RenderingSystem
            self.render_system = RenderingSystem(
                self.scene.application.screen,
                self.scene.world,
                lights_engine=getattr(self.scene.application, "lights_engine", None),
            )
            self.scene.world.services.register(self.render_system, RenderingSystem)
            self.scene.render_system = self.render_system

            # Update DayNightSystem renderer reference
            if self.day_night_system:
                self.day_night_system.render_system = self.render_system

        # Update local UI Manager
        self.scene.ui_manager.set_window_resolution((event.width, event.height))

        # Update HUD layout
        if self.hud:
            self.hud.resize(event.width, event.height)

        # Invalidate hud_surface to force recreation in render()
        if hasattr(self.scene, "hud_surface"):
            del self.scene.hud_surface
            if hasattr(self.scene, "hud_texture"):
                del self.scene.hud_texture

    def update(self, dt: float) -> None:
        """Updates the HUD FPS tracker."""
        if self.scene.application.headless or not self.hud:
            return
            
        self.hud.fps_timer = getattr(self.hud, "fps_timer", 0.0) + dt
        if self.hud.fps_timer >= 0.25:
            # Cast clock to Any since get_fps is valid but mypy might miss internal state
            clock: Any = self.scene.application.clock
            self.hud.fps = clock.get_fps()
            self.hud.fps_timer = 0.0

        self.hud.update(dt)

    def render(self, alpha: float) -> None:
        """
        Renders the game world and HUD.

        Args:
            alpha (float): Interpolation factor (0.0 to 1.0).
        """
        if self.render_system:
            self.render_system.render(self.scene.world, alpha)

        if not self.scene.application.headless and self.hud and self.scene.application.screen:
            self.hud.draw(self.scene.application.screen)
            self.scene.ui_manager.draw_ui(self.scene.application.screen)
