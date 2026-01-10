"""
Scene Manager Module.
"""

from typing import Optional, TYPE_CHECKING, Any
import pygame
import msgspec
from loguru import logger
from .scene import Scene, SceneContext
from .migration import MigrationRegistry

if TYPE_CHECKING:
    pass


class SceneManager:
    """
    Manages a stack of Scene objects and handles global persistence state.
    """

    def __init__(self) -> None:
        """Initializes the SceneManager."""
        self._scenes: list[Scene] = []
        self.persistent_data: dict[str, Any] = {}

    @property
    def current_scene(self) -> Optional["Scene"]:
        """
        Gets the current active scene (the one on top of the stack).

        Returns:
            Optional[Scene]: The current scene, or None if the stack is empty.
        """
        return self._scenes[-1] if self._scenes else None

    def push(self, scene: "Scene") -> None:
        """
        Push a new scene onto the stack.

        Args:
            scene (Scene): The scene to push.

        Returns:
            None
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

        Returns:
            None
        """
        if self._scenes:
            scene = self._scenes.pop()
            scene.on_exit()

    def replace(self, scene: "Scene") -> None:
        """
        Replace the current scene with a new one.

        Args:
            scene (Scene): The new scene.

        Returns:
            None
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
        # Iterate over the dependencies declared by the Scene class (via INJECTIONS ClassVar).
        # This allows declarative dependency injection.
        for key, expected_type in scene.INJECTIONS.items():
            if key in self.persistent_data:
                data = self.persistent_data[key]

                # Check if we need to hydrate a raw dictionary (from a save file)
                if isinstance(data, dict):
                    try:
                        # 1. Check Version & Migrate
                        # Assuming expected_type has a _version_ ClassVar
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

                        # 2. Clean metadata before strict conversion
                        # msgspec/dataclasses don't want '_version_' in the init arguments
                        # unless it's an explicit field.
                        hydration_data = data.copy()
                        hydration_data.pop("_version_", None)

                        # 3. Convert
                        # msgspec.convert is highly efficient and validates the schema
                        obj = msgspec.convert(hydration_data, expected_type)

                        # 4. Update memory with the hydrated object
                        # This ensures subsequent access uses the live object, preventing re-hydration overhead
                        # and maintaining object identity within the session.
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
                    # It is already a live object (runtime transition)
                    context_data[key] = data
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

        Returns:
            None
        """
        if self.current_scene:
            self.current_scene.update(dt)

    def render(self) -> None:
        """
        Render the current scene.

        Returns:
            None
        """
        if self.current_scene:
            self.current_scene.render()

    def handle_event(self, event: pygame.event.Event) -> None:
        """
        Handle events in the current scene.

        Args:
            event (pygame.event.Event): The pygame event.

        Returns:
            None
        """
        if self.current_scene:
            self.current_scene.handle_event(event)

    def set_global_data(self, key: str, value: Any) -> None:
        """
        Sets a global persistent data value.

        Args:
            key (str): The key for the data.
            value (Any): The value to store.

        Returns:
            None
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

        Returns:
            None
        """
        try:
            # We need to serialize the values in persistent_data.
            # Some might be objects, some primitives.
            serialized_data = {}
            for k, v in self.persistent_data.items():
                if hasattr(v, "__dataclass_fields__") or isinstance(v, msgspec.Struct):
                    encoded = msgspec.to_builtins(v)
                    # Inject version
                    if hasattr(type(v), "_version_"):
                        encoded["_version_"] = getattr(type(v), "_version_")
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

        Returns:
            None
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
