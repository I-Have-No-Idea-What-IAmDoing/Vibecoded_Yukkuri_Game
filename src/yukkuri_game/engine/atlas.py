import pygame
from loguru import logger


class AtlasNode:
    """
    A node in the recursive packing tree.

    Attributes:
        rc (pygame.Rect): The rectangle of this node.
        child (tuple[AtlasNode, AtlasNode] | None): The children nodes.
        image_id (str | None): The ID of the image stored in this node.
    """

    __slots__ = ["rc", "child", "image_id"]

    def __init__(self, rc: pygame.Rect):
        self.rc = rc
        self.child: tuple["AtlasNode", "AtlasNode"] | None = None
        self.image_id: str | None = None

    def insert(self, img_id: str, width: int, height: int) -> pygame.Rect | None:
        """
        Inserts an image into the atlas node.

        Args:
            img_id (str): The ID of the image.
            width (int): Image width.
            height (int): Image height.

        Returns:
            pygame.Rect | None: The rectangle where the image was inserted, or None if full.
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
        size (tuple[int, int]): Size of the atlas.
        surface (pygame.Surface): The atlas surface.
        root (AtlasNode): Root node of the packing tree.
        mapping (dict[str, pygame.Rect]): Map of image names to rects.
        failed_to_pack (list[str]): List of images that failed to pack.
    """

    def __init__(self, size: tuple[int, int] = (2048, 2048)):
        """
        Initializes the TextureAtlas.

        Args:
            size (tuple[int, int]): The size of the atlas surface.
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
            name (str): The name of the image.
            surface (pygame.Surface): The image surface.

        Returns:
            pygame.Rect | None: The occupied rectangle, or None if full.
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
        Returns a subsurface for the given image name.

        Args:
            name (str): The name of the image.

        Returns:
            pygame.Surface | None: The subsurface, or None if not found.
        """
        rect = self.mapping.get(name)
        if rect:
            return self.surface.subsurface(rect)
        return None
