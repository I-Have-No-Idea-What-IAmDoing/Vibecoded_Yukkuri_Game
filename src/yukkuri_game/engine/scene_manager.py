"""
Scene Manager Module.
"""

import gc
from typing import TYPE_CHECKING, Any

import msgspec
import pygame
from loguru import logger

from .migration import MigrationRegistry
from .scene import Scene, SceneContext

if TYPE_CHECKING:
    pass


class SceneManager:
    """
    Manages a stack of Scene objects and handles global persistence state.

    Attributes:
        _scenes (list[Scene]): The stack of active scenes.
        persistent_data (dict[str, Any]): Global data shared across scenes.
    """

    def __init__(self) -> None:
        """Initializes the SceneManager."""
        self._scenes: list[Scene] = []
        self.persistent_data: dict[str, Any] = {}

    @property
    def current_scene(self) -> Scene | None:
        """
        Gets the current active scene (the one on top of the stack).

        Returns:
            Scene | None: The current scene, or None if the stack is empty.
        """
        return self._scenes[-1] if self._scenes else None

    def push(self, scene: "Scene") -> None:
        """
        Push a new scene onto the stack.

        Args:
            scene (Scene): The scene to push.
        """
        context = self._prepare_context(scene)

        # Call setup with context
        scene.setup(context)

        self._scenes.append(scene)
        scene.on_enter()

    def pop(self) -> None:
        """
        Pop the current scene from the stack.

        Calls on_exit() on the popped scene.
        """
        if self._scenes:
            scene = self._scenes.pop()
            scene.on_exit()
            scene.destroy()
            gc.collect()  # Break cyclic references (Events -> Handlers -> Scene).

    def replace(self, scene: "Scene") -> None:
        """
        Replace the current scene with a new one.

        Args:
            scene (Scene): The new scene.
        """
        if self._scenes:
            self.pop()
        self.push(scene)

    def _prepare_context(self, scene: Scene) -> SceneContext:
        """
        Resolves dependencies declared by the Scene and creates the Context.
        Handles data migration and deserialization if data is in raw dict form.

        This method performs "Just-In-Time" hydration:
        If the data in persistent_data is a raw dictionary (from a loaded file),
        it attempts to convert it to the `expected_type` requested by the scene,
        running any necessary migrations first.

        Args:
            scene (Scene): The scene requesting dependencies.

        Returns:
            SceneContext: The context containing injected dependencies.

        Raises:
            RuntimeError: If data corruption or incompatible versions are detected.
        """
        context_data = {}
        # Iterate over declared INJECTIONS; performs JIT hydration from raw dicts.
        for key, expected_type in scene.INJECTIONS.items():
            if key in self.persistent_data:
                data = self.persistent_data[key]

                if isinstance(data, dict):
                    try:
                        target_version = getattr(expected_type, "_version_", 0)
                        saved_version = data.get("_version_", 0)

                        if saved_version < target_version:
                            logger.info(
                                f"Migrating {key} from v{saved_version} to v{target_version}"
                            )
                            data = MigrationRegistry.migrate(
                                expected_type.__name__,
                                data,
                                saved_version,
                                target_version,
                            )

                        # Clean metadata before strict conversion.
                        hydration_data = data.copy()
                        hydration_data.pop("_version_", None)

                        obj = msgspec.convert(hydration_data, expected_type)

                        # Cache hydrated object to avoid re-hydration.
                        context_data[key] = obj
                        self.persistent_data[key] = obj

                    except Exception as e:
                        logger.critical(
                            f"Failed to inject/deserialize '{key}' for {type(scene).__name__}. Error: {e}"
                        )
                        # Determine fallback strategy: Crash or Skip?
                        # Crashing is safer than running with corrupt/wrong-type data.
                        raise RuntimeError(
                            f"Data corruption detected for key '{key}'"
                        ) from e
                else:
                    context_data[key] = data  # Already a live object.
            else:
                logger.warning(
                    f"Scene {type(scene).__name__} requested injection '{key}' but it was not found."
                )

        return SceneContext(data=context_data)

    def update(self, dt: float) -> None:
        """
        Update the current scene.

        Args:
            dt (float): Delta time in seconds.
        """
        if self.current_scene:
            self.current_scene.update(dt)

    def render(self) -> None:
        """Render the current scene."""
        if self.current_scene:
            self.current_scene.render()

    def handle_event(self, event: pygame.event.Event) -> None:
        """
        Handle events in the current scene.

        Args:
            event (pygame.event.Event): The pygame event.
        """
        if self.current_scene:
            self.current_scene.handle_event(event)

    def set_global_data(self, key: str, value: Any) -> None:
        """
        Sets a global persistent data value.

        Args:
            key (str): The key for the data.
            value (Any): The value to store.
        """
        self.persistent_data[key] = value

    def get_global_data(self, key: str, default: Any = None) -> Any:
        """
        Gets a global persistent data value.

        Args:
            key (str): The key to retrieve.
            default (Any): The default value if the key is not found. Defaults to None.

        Returns:
            Any: The stored value or the default.
        """
        return self.persistent_data.get(key, default)

    def save_global_data(self, filepath: str) -> None:
        """
        Saves the global persistent data to a file.

        Args:
            filepath (str): The path to the file to save to.
        """
        try:
            serialized_data = {}
            for k, v in self.persistent_data.items():
                if hasattr(v, "__dataclass_fields__") or isinstance(v, msgspec.Struct):
                    encoded = msgspec.to_builtins(v)
                    if hasattr(type(v), "_version_"):
                        encoded["_version_"] = getattr(
                            type(v), "_version_"
                        )  # Inject version.
                    serialized_data[k] = encoded
                else:
                    serialized_data[k] = v

            with open(filepath, "wb") as f:
                f.write(msgspec.msgpack.encode(serialized_data))
            logger.info(f"Saved global data to {filepath}")
        except Exception as e:
            logger.error(f"Failed to save global data: {e}")

    def load_global_data(self, filepath: str) -> None:
        """
        Loads the global persistent data from a file.

        Args:
            filepath (str): The path to the file to load from.
        """
        try:
            with open(filepath, "rb") as f:
                data = msgspec.msgpack.decode(f.read())
                if isinstance(data, dict):
                    self.persistent_data = data
                    logger.info(f"Loaded global data from {filepath}")
                else:
                    logger.error(f"Invalid global data file format: {filepath}")
        except FileNotFoundError:
            logger.warning(f"Global data file {filepath} not found.")
        except Exception as e:
            logger.error(f"Failed to load global data: {e}")
