import pygame
from typing import Tuple, Optional, Dict, List
from loguru import logger


class AtlasNode:
    """
    A node in the recursive packing tree.
    """

    __slots__ = ["rc", "child", "image_id"]

    def __init__(self, rc: pygame.Rect):
        self.rc = rc
        self.child: Optional[Tuple["AtlasNode", "AtlasNode"]] = None
        self.image_id: Optional[str] = None

    def insert(self, img_id: str, width: int, height: int) -> Optional[pygame.Rect]:
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
            # Split vertically (left part is width x height, right part is remaining)
            # Actually, standard algorithm: split into two rectangles.
            # 1. (x, y, width, height) <- this is where we want to put it? No we split the SPACE.
            # We split into two children: One that matches the image size (plus remainder in one dimension) and one that is the rest?
            # Standard lightmap packing:
            # Child 0: (x, y, width, rect.h) -> Split this further?
            # Let's try explicit split:
            # Child 0 (Left): (x, y, width, rect.h)
            # Child 1 (Right): (x+width, y, rem_w, rect.h)
            # Then Child 0 needs to be split horizontally to fit height?

            # recursive approach:

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
    """

    def __init__(self, size: Tuple[int, int] = (2048, 2048)):
        self.size = size
        self.surface = pygame.Surface(size, pygame.SRCALPHA)
        self.root = AtlasNode(pygame.Rect(0, 0, size[0], size[1]))
        self.mapping: Dict[str, pygame.Rect] = {}
        self.failed_to_pack: List[str] = []

    def add_image(self, name: str, surface: pygame.Surface) -> Optional[pygame.Rect]:
        """
        Adds an image to the atlas. Returns the Rect it occupied, or None if full.
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

    def get_region(self, name: str) -> Optional[pygame.Surface]:
        """
        Returns a subsurface for the given image name.
        """
        rect = self.mapping.get(name)
        if rect:
            return self.surface.subsurface(rect)
        return None
