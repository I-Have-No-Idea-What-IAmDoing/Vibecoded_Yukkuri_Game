"""
Texture Atlas Module.

This module provides the `TextureAtlas` class for packing multiple small images
(sprites) into a single large texture (atlas) to optimize rendering performance.
"""

import pygame
from loguru import logger


class AtlasNode:
    """
    A node in the recursive packing tree (BSP-like structure).

    Used to find free space in the texture atlas for new images.

    Attributes:
        rc (pygame.Rect): The rectangle representing this node's space.
        child (tuple[AtlasNode, AtlasNode] | None): The children nodes (left/right or top/bottom).
        image_id (str | None): The ID of the image stored in this node, if any.
    """

    __slots__ = ["rc", "child", "image_id"]

    def __init__(self, rc: pygame.Rect) -> None:
        """
        Initializes an AtlasNode.

        Args:
            rc (pygame.Rect): The rectangle for this node.
        """
        self.rc = rc
        self.child: tuple["AtlasNode", "AtlasNode"] | None = None
        self.image_id: str | None = None

    def insert(self, img_id: str, width: int, height: int) -> pygame.Rect | None:
        """
        Attempts to insert an image into this node or its children.

        Args:
            img_id (str): The unique identifier for the image.
            width (int): The width of the image.
            height (int): The height of the image.

        Returns:
            pygame.Rect | None: The rectangle where the image was packed, or None if it didn't fit.
        """
        # If not a leaf, try inserting into children
        if self.child:
            res = self.child[0].insert(img_id, width, height)
            if res:
                return res
            return self.child[1].insert(img_id, width, height)

        # If used, we can't fit here
        if self.image_id is not None:
            return None

        # Check if it fits
        if width > self.rc.width or height > self.rc.height:
            return None

        # Exact fit
        if width == self.rc.width and height == self.rc.height:
            self.image_id = img_id
            return self.rc

        # Split
        dw = self.rc.width - width
        dh = self.rc.height - height

        if dw > dh:
            # Split vertically
            c1 = AtlasNode(pygame.Rect(self.rc.x, self.rc.y, width, self.rc.height))
            c2 = AtlasNode(
                pygame.Rect(self.rc.x + width, self.rc.y, dw, self.rc.height)
            )
            self.child = (c1, c2)

            # Now insert into c1 (which has correct width, but maybe wrong height)
            return self.child[0].insert(img_id, width, height)
        else:
            # Split horizontally
            c1 = AtlasNode(pygame.Rect(self.rc.x, self.rc.y, self.rc.width, height))
            c2 = AtlasNode(
                pygame.Rect(self.rc.x, self.rc.y + height, self.rc.width, dh)
            )
            self.child = (c1, c2)
            return self.child[0].insert(img_id, width, height)


class TextureAtlas:
    """
    Manages a large surface composed of many smaller textures.

    Attributes:
        size (tuple[int, int]): The dimensions of the atlas surface.
        surface (pygame.Surface): The main atlas surface.
        root (AtlasNode): The root node of the packing tree.
        mapping (dict[str, pygame.Rect]): Map of image names to their rectangles.
        failed_to_pack (list[str]): List of image names that failed to pack.
    """

    def __init__(self, size: tuple[int, int] = (2048, 2048)) -> None:
        """
        Initializes the TextureAtlas.

        Args:
            size (tuple[int, int]): The dimensions of the atlas. Defaults to (2048, 2048).
        """
        self.size = size
        self.surface = pygame.Surface(size, pygame.SRCALPHA)
        self.root = AtlasNode(pygame.Rect(0, 0, size[0], size[1]))
        self.mapping: dict[str, pygame.Rect] = {}
        self.failed_to_pack: list[str] = []

    def add_image(self, name: str, surface: pygame.Surface) -> pygame.Rect | None:
        """
        Adds an image to the atlas.

        Args:
            name (str): The unique name of the image.
            surface (pygame.Surface): The image surface to add.

        Returns:
            pygame.Rect | None: The rectangle occupied by the image, or None if the atlas is full.
        """
        # Add 1px padding to avoid bleeding? Let's assume 0 for pixel art for now for exactness,
        # but usually 1px padding is good. Let's do 0 for simplicity of exact Rects.
        w, h = surface.get_size()

        rect = self.root.insert(name, w, h)
        if rect:
            self.surface.blit(surface, rect)
            self.mapping[name] = rect
            return rect
        else:
            logger.warning(f"TextureAtlas full! Could not fit {name} ({w}x{h})")
            self.failed_to_pack.append(name)
            return None

    def get_region(self, name: str) -> pygame.Surface | None:
        """
        Retrieves a subsurface for the given image name.

        Args:
            name (str): The name of the image to retrieve.

        Returns:
            pygame.Surface | None: The subsurface containing the image, or None if not found.
        """
        rect = self.mapping.get(name)
        if rect:
            return self.surface.subsurface(rect)
        return None
