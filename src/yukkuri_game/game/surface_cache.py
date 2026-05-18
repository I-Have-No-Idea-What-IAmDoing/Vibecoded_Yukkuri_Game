"""Module for caching transformed surfaces to optimize rendering."""

import pygame
from ..engine.resource_manager import ResourceManager


class SurfaceCache:
    """
    Manages a cache of transformed surfaces (scaled, rotated, flipped).
    Uses an LRU (Least Recently Used) eviction policy.
    """

    def __init__(self, resource_manager: ResourceManager, max_size: int = 200):
        """
        Initializes the SurfaceCache.

        Args:
            resource_manager (ResourceManager): The resource manager to fetch base images.
            max_size (int): The maximum number of surfaces to cache.
        """
        self.rm = resource_manager
        self.max_size = max_size
        # Key: (image_name, frame, width, height, scale, rotation, flip_x, flip_y)
        # Uses plain dict (insertion-ordered since Python 3.7) for LRU.
        self._cache: dict[
            tuple[str, int, int, int, float, float, bool, bool], pygame.Surface
        ] = {}

    def get_surface(
        self,
        image_name: str,
        frame_index: int,
        frame_count: int,
        sprite_width: int,
        sprite_height: int,
        scale: float,
        rotation: float,
        flip_x: bool,
        flip_y: bool,
    ) -> pygame.Surface | None:
        """
        Retrieves a cached surface or creates a new one if not found.

        Args:
            image_name (str): The name of the base image.
            frame_index (int): The current frame index.
            frame_count (int): Total frames (used to determine if slicing is needed).
            sprite_width (int): Width of a single sprite frame.
            sprite_height (int): Height of a single sprite frame.
            scale (float): Scaling factor.
            rotation (float): Rotation angle in degrees.
            flip_x (bool): Whether to flip horizontally.
            flip_y (bool): Whether to flip vertically.

        Returns:
            Optional[pygame.Surface]: The transformed surface.
        """
        key = (
            image_name,
            frame_index,
            sprite_width,
            sprite_height,
            round(scale, 3),
            round(rotation, 1),
            flip_x,
            flip_y,
        )

        if key in self._cache:
            # Move to end (mark as recently used) via pop + re-insert
            val = self._cache.pop(key)
            self._cache[key] = val
            return self._cache[key]

        # Not in cache, create it
        surface = self._create_surface(
            image_name,
            frame_index,
            frame_count,
            sprite_width,
            sprite_height,
            scale,
            rotation,
            flip_x,
            flip_y,
        )

        if surface:
            self._cache[key] = surface
            if len(self._cache) > self.max_size:
                # Remove the oldest item (first key in dict)
                oldest = next(iter(self._cache))
                del self._cache[oldest]

        return surface

    def _create_surface(
        self,
        image_name: str,
        frame_index: int,
        frame_count: int,
        sprite_width: int,
        sprite_height: int,
        scale: float,
        rotation: float,
        flip_x: bool,
        flip_y: bool,
    ) -> pygame.Surface | None:
        """
        Creates the transformed surface.

        Args:
            image_name (str): The name of the base image.
            frame_index (int): The current frame index.
            frame_count (int): Total frames.
            sprite_width (int): Width of a single sprite frame.
            sprite_height (int): Height of a single sprite frame.
            scale (float): Scaling factor.
            rotation (float): Rotation angle in degrees.
            flip_x (bool): Whether to flip horizontally.
            flip_y (bool): Whether to flip vertically.

        Returns:
            Optional[pygame.Surface]: The newly created surface, or None if creation failed.
        """
        img = self.rm.load_image(image_name)
        img_width, img_height = img.get_size()

        # Handle animation / slicing
        if frame_count > 1:
            source_rect = pygame.Rect(0, 0, sprite_width, sprite_height)
            sx = frame_index * sprite_width
            if sx + sprite_width <= img_width:
                source_rect.x = sx

            # Ensure source_rect is within image bounds
            if source_rect.right > img_width or source_rect.bottom > img_height:
                if img_width < sprite_width or img_height < sprite_height:
                    frame_img = pygame.transform.scale(
                        img, (sprite_width, sprite_height)
                    )
                else:
                    frame_img = img.subsurface(source_rect.clip(img.get_rect()))
            else:
                frame_img = img.subsurface(source_rect)
        else:
            if img_width != sprite_width or img_height != sprite_height:
                frame_img = pygame.transform.scale(img, (sprite_width, sprite_height))
            else:
                frame_img = img

        # Apply flips
        if flip_x or flip_y:
            frame_img = pygame.transform.flip(frame_img, flip_x, flip_y)

        # Apply Scale
        if scale != 1.0:
            w = int(frame_img.get_width() * scale)
            h = int(frame_img.get_height() * scale)
            if w > 0 and h > 0:
                scaled_img = pygame.transform.scale(frame_img, (w, h))
            else:
                return None  # Invalid size
        else:
            scaled_img = frame_img

        # Apply Rotation
        if rotation != 0.0:
            scaled_img = pygame.transform.rotate(scaled_img, rotation)

        return scaled_img

    def clear(self) -> None:
        """Clears the cache."""
        self._cache.clear()
