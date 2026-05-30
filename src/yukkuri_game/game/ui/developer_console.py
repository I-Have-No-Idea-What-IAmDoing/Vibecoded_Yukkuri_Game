"""
Developer Console UI Module.

Provides an interactive console window for developer command execution
and raw Python expression evaluation within the ECS environment.
"""

import html
import sys
import traceback
from typing import Any

from loguru import logger
import pygame
import pygame_gui
from pygame_gui.core import ObjectID
from pygame_gui.elements import UITextBox
from pygame_gui.elements import UITextEntryLine
from pygame_gui.elements import UIWindow

from ...engine.ecs import World
from ..services import EconomyService


class DeveloperConsole:
    """
    Floating console window allowing for command execution and live script eval.
    """

    def __init__(
        self,
        manager: pygame_gui.UIManager,
        world: World,
        hud: Any,
    ) -> None:
        """
        Initializes the Developer Console.

        Args:
            manager: The Pygame GUI UI Manager.
            world: The ECS World instance.
            hud: The gameplay HUD instance.
        """
        self.manager: pygame_gui.UIManager = manager
        self.world: World = world
        self.hud: Any = hud

        self.window: UIWindow | None = None
        self.output_box: UITextBox | None = None
        self.input_line: UITextEntryLine | None = None

        self.history: list[str] = []
        self.history_index: int = 0
        self.output_buffer: str = (
            "<b>Developer Console Initialized.</b> "
            "Type /help for options.<br>"
        )

        self.sink_id: int | None = None

        # Sandboxed execution environments
        self.globals_env: dict[str, Any] = {
            "__builtins__": __builtins__,
            "math": __import__("math"),
            "random": __import__("random"),
            "sys": __import__("sys"),
            "time": __import__("time"),
            "pygame": __import__("pygame"),
            "world": self.world,
            "services": self.world.services,
            "spawn": self._env_spawn,
            "help": self._env_help,
        }

    def open(self) -> None:
        """
        Opens the Developer Console window and registers the Loguru sink.
        """
        if self.window:
            return

        from ...engine.input_manager import InputManager

        im = self.world.services.try_get(InputManager)
        if im:
            im.clear_pressed_states()

        self.window = UIWindow(
            rect=pygame.Rect(50, 50, 700, 480),
            manager=self.manager,
            window_display_title="Developer Console",
            resizable=False,
            object_id=ObjectID(object_id="#developer_console"),
        )

        self.output_box = UITextBox(
            html_text=self.output_buffer,
            relative_rect=pygame.Rect(5, 5, 680, 390),
            manager=self.manager,
            container=self.window,
            object_id=ObjectID(class_id="console_output"),
        )

        self.input_line = UITextEntryLine(
            relative_rect=pygame.Rect(5, 405, 680, 30),
            manager=self.manager,
            container=self.window,
            object_id=ObjectID(class_id="console_input"),
        )

        # Register loguru sink
        self.sink_id = logger.add(
            self._loguru_sink,
            level="DEBUG" if self.world.debug_timing else "INFO",
            colorize=False,
            format="{time:HH:mm:ss} | {level: <8} | {message}",
        )

        # Auto-focus the input line
        self.input_line.focus()
        self._scroll_to_bottom()

    def close(self) -> None:
        """
        Closes the console window and cleanly removes the Loguru sink.
        """
        from ...engine.input_manager import InputManager

        im = self.world.services.try_get(InputManager)
        if im:
            im.clear_pressed_states()

        if self.sink_id is not None:
            try:
                logger.remove(self.sink_id)
            except ValueError:
                pass
            self.sink_id = None

        if self.window:
            self.window.kill()
            self.window = None
            self.output_box = None
            self.input_line = None

    def is_open(self) -> bool:
        """
        Checks if the console window is currently open.

        Returns:
            True if the window is instantiated, False otherwise.
        """
        return self.window is not None

    def log(self, html_text: str) -> None:
        """
        Appends text to the console buffer and updates the UITextBox.

        Args:
            html_text: The HTML formatted text string to append.
        """
        self.output_buffer += html_text

        # Avoid buffer bloat
        if len(self.output_buffer) > 60000:
            idx = self.output_buffer.find("<br>", 20000)
            if idx != -1:
                self.output_buffer = self.output_buffer[idx + 4 :]

        if self.window and self.output_box:
            self.output_box.append_html_text(html_text)
            self._scroll_to_bottom()

    def _scroll_to_bottom(self) -> None:
        """
        Scrolls the output text box viewport to the bottom.
        """
        if (
            self.output_box
            and hasattr(self.output_box, "scroll_bar")
            and self.output_box.scroll_bar
        ):
            try:
                self.output_box.scroll_bar.scroll_position = (
                    self.output_box.scroll_bar.scrollable_height
                )
                self.output_box.scroll_bar.update(0)
                self.output_box.scroll_bar.set_scroll_from_start_percentage(
                    1.0
                )
            except Exception:
                pass

    def _loguru_sink(self, message: Any) -> None:
        """
        Loguru sink callback for chronological console logs mapping.

        Args:
            message: The message record from Loguru.
        """
        try:
            record = message.record
            level = record["level"].name
            msg_str = record["message"]

            if level == "DEBUG":
                color = "#565f89"
            elif level == "WARNING":
                color = "#e0af68"
            elif level == "ERROR" or level == "CRITICAL":
                color = "#f7768e"
            else:
                color = "#c0caf5"

            msg_escaped = html.escape(msg_str)
            time_str = record["time"].strftime("%H:%M:%S")
            origin = f"{record['name']}:{record['line']}"

            formatted = (
                f"<font color='#565f89'>[{time_str}]</font> "
                f"<font color='{color}'>[{level:<8}]</font> "
                f"<font color='#7aa2f7'>[{origin}]</font> — "
                f"<font color='{color}'>{msg_escaped}</font><br>"
            )
            self.log(formatted)
        except Exception:
            self.log(
                f"<font color='#c0caf5'>{str(message).strip()}</font><br>"
            )

    def execute_command(self, text: str) -> None:
        """
        Processes a user-submitted command or Python script block.

        Args:
            text: The raw command string to evaluate.
        """
        text = text.strip()
        if not text:
            return

        self.history.append(text)
        self.history_index = len(self.history)

        if text.startswith("/"):
            self.execute_slash_command(text)
        else:
            self.execute_python(text)

    def execute_slash_command(self, text: str) -> None:
        """
        Evaluates a slash cheat shortcut.

        Args:
            text: The command string beginning with a slash.
        """
        self.log(f"<font color='#bb9af7'>&gt; {text}</font><br>")
        parts = text[1:].split()
        if not parts:
            return

        cmd = parts[0].lower()
        args = parts[1:]

        if cmd == "help":
            self._cmd_help()
        elif cmd == "clear":
            self.output_buffer = ""
            self.log("")
        elif cmd == "pause":
            self._cmd_pause()
        elif cmd == "money":
            self._cmd_money(args)
        elif cmd == "speed":
            self._cmd_speed(args)
        elif cmd == "spawn":
            self._cmd_spawn(args)
        elif cmd == "kill":
            self._cmd_kill(args)
        elif cmd == "set":
            self._cmd_set(args)
        else:
            self.log(
                f"<font color='#f7768e'>Unknown slash command: {cmd}</font><br>"
            )

    def execute_python(self, code: str) -> None:
        """
        Runs unprefixed commands as raw Python blocks with stdout redirection.

        Args:
            code: The Python script string to compile and run.
        """
        self.log(f"<font color='#7aa2f7'>&gt;&gt;&gt; {code}</font><br>")

        self.globals_env["print"] = lambda *args, sep=" ": self.log(
            "<font color='#9ece6a'>"
            + sep.join(map(str, args))
            + "</font><br>"
        )

        try:
            try:
                compiled = compile(code, "<console>", "eval")
                result = eval(compiled, self.globals_env)
                if result is not None:
                    self.log(
                        f"<font color='#b4f9f8'>{repr(result)}</font><br>"
                    )
            except SyntaxError:
                compiled = compile(code, "<console>", "exec")
                exec(compiled, self.globals_env)
        except Exception:
            exc_type, exc_value, exc_tb = sys.exc_info()
            tb_lines = traceback.format_exception(
                exc_type, exc_value, exc_tb
            )
            tb_str = "".join(tb_lines)
            self.log(
                f"<font color='#f7768e'>{html.escape(tb_str)}</font><br>"
            )

    def _cmd_help(self) -> None:
        """Prints available slash shortcuts."""
        help_text = (
            "<font color='#73daca'><b>Available Console Commands:</b></font><br>"
            "  /help - Display this documentation.<br>"
            "  /clear - Clear the log viewport.<br>"
            "  /pause - Toggle paused simulation state.<br>"
            "  /money &lt;amount&gt; - Set/adjust funds (e.g. /money +5000).<br>"
            "  /speed &lt;scale&gt; - Alter simulation speed (e.g. /speed 2.0).<br>"
            "  /spawn &lt;type&gt; [x] [y] - Spawn yukkuri/item at location.<br>"
            "  /kill &lt;entity_id&gt; - Destroy an entity cleanly.<br>"
            "  /set &lt;stat&gt; &lt;val&gt; - Set stats on selected entities.<br>"
            "  &lt;python_expr&gt; - Any non-slashed line is evaluated as Python.<br>"
        )
        self.log(help_text)

    def _cmd_pause(self) -> None:
        """Toggles the paused gameplay session state."""
        if self.hud and hasattr(self.hud, "scene") and self.hud.scene:
            scene = self.hud.scene
            if scene.session_manager:
                scene.session_manager.toggle_pause()
                state = (
                    "PAUSED" if scene.session_manager.paused else "UNPAUSED"
                )
                self.log(
                    f"<font color='#9ece6a'>Game simulation is now {state}.</font><br>"
                )
                return
        self.log(
            "<font color='#f7768e'>Error: SessionManager not accessible.</font><br>"
        )

    def _cmd_money(self, args: list[str]) -> None:
        """
        Adjusts player funds in the economy service.

        Args:
            args: Command arguments containing the amount modifier.
        """
        if not args:
            self.log(
                "<font color='#f7768e'>Error: /money <amount></font><br>"
            )
            return

        arg = args[0]
        try:
            is_relative = arg.startswith("+") or arg.startswith("-")
            val = int(arg)
            economy = self.world.services.get(EconomyService)

            if is_relative:
                if val >= 0:
                    economy.add_money(val)
                else:
                    economy.remove_money(-val)
            else:
                economy.set_money(val)

            self.log(
                f"<font color='#9ece6a'>Money adjusted. "
                f"New balance: ${economy.money}</font><br>"
            )
        except ValueError as e:
            self.log(
                f"<font color='#f7768e'>Error parsing amount: {e}</font><br>"
            )

    def _cmd_speed(self, args: list[str]) -> None:
        """
        Alters simulation speed scale.

        Args:
            args: Command arguments containing speed factor multiplier.
        """
        if not args:
            self.log("<font color='#f7768e'>Error: /speed <scale></font><br>")
            return

        try:
            scale = float(args[0])
            if (
                self.hud
                and hasattr(self.hud, "scene")
                and self.hud.scene
                and self.hud.scene.session_manager
            ):
                self.hud.scene.session_manager.time_scale = scale
                self.log(
                    f"<font color='#9ece6a'>Speed multiplier set "
                    f"to {scale}x.</font><br>"
                )
            else:
                self.log(
                    "<font color='#f7768e'>Error: SessionManager "
                    "not found.</font><br>"
                )
        except ValueError as e:
            self.log(
                f"<font color='#f7768e'>Error parsing speed: {e}</font><br>"
            )

    def _cmd_spawn(self, args: list[str]) -> None:
        """
        Spawns a prefab at given coordinates or screen center.

        Args:
            args: Prefab arguments containing type ID and optional x, y.
        """
        if not args:
            self.log(
                "<font color='#f7768e'>Error: /spawn <type_id> "
                "[x] [y]</font><br>"
            )
            return

        type_id = args[0]
        try:
            x, y = self._env_spawn(
                type_id,
                args[1] if len(args) > 1 else None,
                args[2] if len(args) > 2 else None,
            )
            self.log(
                f"<font color='#9ece6a'>Spawned '{type_id}' at position "
                f"({x:.1f}, {y:.1f}).</font><br>"
            )
        except Exception as e:
            self.log(
                f"<font color='#f7768e'>Failed to spawn prefab: {e}</font><br>"
            )

    def _env_spawn(
        self,
        type_id: str,
        x_str: str | None = None,
        y_str: str | None = None,
    ) -> tuple[float, float]:
        """
        Helper method to spawn prefab, exposed inside raw Python environment.

        Args:
            type_id: The ID string of the prefab type.
            x_str: Optional x coordinate as string/numeric.
            y_str: Optional y coordinate as string/numeric.

        Returns:
            Resolved x, y world coordinates.
        """
        from ...engine.camera import Camera
        from ...game.prefabs.yukkuri import create_yukkuri

        cam = self.world.services.try_get(Camera)

        x = (
            float(x_str)
            if x_str is not None
            else (cam.camera_x if cam else 400.0)
        )
        y = (
            float(y_str)
            if y_str is not None
            else (cam.camera_y if cam else 300.0)
        )

        from ...engine.resource_manager import ResourceManager

        rm = self.world.services.try_get(ResourceManager)
        is_item = False
        if rm and type_id in rm.item_types:
            is_item = True

        if is_item:
            from ...game.prefabs.item import create_item

            create_item(self.world, type_id, x, y)
        else:
            create_yukkuri(self.world, type_id, x, y)

        return x, y

    def _env_help(self, *args: Any, **kwargs: Any) -> str:
        """
        Overrides interactive help() to prevent main thread blocking freezes.

        Args:
            *args: Variable arguments.
            **kwargs: Keyword arguments.

        Returns:
            A status string.
        """
        self._cmd_help()
        return "Type /help or help() for commands."

    def _cmd_kill(self, args: list[str]) -> None:
        """
        Cleanly destroys an active entity.

        Args:
            args: Command arguments containing entity ID.
        """
        if not args:
            self.log(
                "<font color='#f7768e'>Error: /kill <entity_id></font><br>"
            )
            return

        try:
            ent_id = int(args[0])
            if self.world.entity_exists(ent_id):
                self.world.destroy_entity(ent_id)
                self.log(
                    f"<font color='#9ece6a'>Entity {ent_id} destroyed.</font><br>"
                )
            else:
                self.log(
                    f"<font color='#f7768e'>Error: Entity {ent_id} "
                    "does not exist.</font><br>"
                )
        except ValueError as e:
            self.log(
                f"<font color='#f7768e'>Error parsing ID: {e}</font><br>"
            )

    def _cmd_set(self, args: list[str]) -> None:
        """
        Sets statistical component fields on the selected entities.

        Args:
            args: Stat name and value modification parameters.
        """
        if len(args) < 2:
            self.log(
                "<font color='#f7768e'>Error: /set <stat> <value></font><br>"
            )
            return

        stat_name = args[0].lower()
        val_str = args[1]

        if not self.hud or not self.hud.selected_entities:
            self.log(
                "<font color='#e0af68'>Warning: No active entities "
                "selected.</font><br>"
            )
            return

        from ..components import YukkuriStats

        try:
            if val_str.lower() in ("true", "yes", "on"):
                val: Any = True
            elif val_str.lower() in ("false", "no", "off"):
                val = False
            elif "." in val_str:
                val = float(val_str)
            else:
                val = int(val_str)
        except ValueError:
            val = val_str

        count = 0
        for entity_id in self.hud.selected_entities:
            stats = self.world.try_get_component(entity_id, YukkuriStats)
            if stats and hasattr(stats, stat_name):
                setattr(stats, stat_name, val)
                count += 1

        if count > 0:
            self.log(
                f"<font color='#9ece6a'>Successfully set {stat_name} = "
                f"{val} on {count} selected entities.</font><br>"
            )
        else:
            self.log(
                f"<font color='#f7768e'>Error: Stat '{stat_name}' not "
                "found on any selected entities.</font><br>"
            )

    def process_event(self, event: pygame.event.Event) -> bool:
        """
        Processes events for the Developer Console.

        Args:
            event: The Pygame event to process.

        Returns:
            True if the event was consumed, False otherwise.
        """
        if not self.is_open():
            return False

        # Handle text entry submissions
        if (
            event.type == pygame_gui.UI_TEXT_ENTRY_FINISHED
            and event.ui_element == self.input_line
        ):
            command = event.text
            if self.input_line:
                self.input_line.set_text("")
            self.execute_command(command)
            # Re-focus immediately
            if self.input_line:
                self.input_line.focus()
            return True

        # Handle window closure
        if (
            event.type == pygame_gui.UI_WINDOW_CLOSE
            and event.ui_element == self.window
        ):
            self.close()
            return True

        # Handle up/down history keys when input line has focus
        if event.type == pygame.KEYDOWN:
            focus_set = self.manager.get_focus_set()
            if focus_set and self.input_line in focus_set:
                if event.key == pygame.K_UP:
                    if self.history:
                        self.history_index = max(0, self.history_index - 1)
                        if self.input_line:
                            self.input_line.set_text(
                                self.history[self.history_index]
                            )
                    return True
                elif event.key == pygame.K_DOWN:
                    if self.history:
                        if self.history_index < len(self.history) - 1:
                            self.history_index += 1
                            if self.input_line:
                                self.input_line.set_text(
                                    self.history[self.history_index]
                                )
                        else:
                            self.history_index = len(self.history)
                            if self.input_line:
                                self.input_line.set_text("")
                    return True

        return False
