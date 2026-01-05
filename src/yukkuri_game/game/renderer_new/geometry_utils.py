import math
import pygame
import pymunk
from typing import List, Tuple, Optional, Dict
from ..components import Transform, Occluder, Sprite, PhysicsBody

class GeometryUtils:
    """Utilities for generating render geometry."""

    CIRCLE_OCCLUDER_SEGMENTS = 12
    _CIRCLE_CACHE: Optional[List[Tuple[float, float]]] = None

    # Cache for static vertices: entity_id -> vertices
    _STATIC_CACHE: Dict[int, List[Tuple[float, float]]] = {}
    # Cache key to invalidate static cache if transform changes
    _STATIC_CACHE_KEYS: Dict[int, Tuple[float, float, float, float]] = {}

    @classmethod
    def get_circle_vertices(cls) -> List[Tuple[float, float]]:
        """Returns cached unit circle vertices."""
        if cls._CIRCLE_CACHE is None:
            cls._CIRCLE_CACHE = []
            for i in range(cls.CIRCLE_OCCLUDER_SEGMENTS):
                angle = 2 * math.pi * i / cls.CIRCLE_OCCLUDER_SEGMENTS
                cls._CIRCLE_CACHE.append((math.cos(angle), math.sin(angle)))
        return cls._CIRCLE_CACHE

    @classmethod
    def get_occluder_vertices(
        cls,
        entity_id: int,
        transform: Transform,
        occluder: Occluder,
        sprite: Optional[Sprite] = None,
        body: Optional[PhysicsBody] = None
    ) -> List[Tuple[float, float]]:
        """
        Calculates world-space vertices for an occluder.
        """
        # Check cache for static objects
        if occluder.static:
            key = (transform.x, transform.y, transform.rotation, transform.scale)
            if entity_id in cls._STATIC_CACHE:
                if entity_id in cls._STATIC_CACHE_KEYS and cls._STATIC_CACHE_KEYS[entity_id] == key:
                    return cls._STATIC_CACHE[entity_id]

            # Update key
            cls._STATIC_CACHE_KEYS[entity_id] = key

        world_vertices = []

        if occluder.polygon:
            # Custom polygon
            rad = math.radians(transform.rotation)
            cos_a = math.cos(rad)
            sin_a = math.sin(rad)

            for vx, vy in occluder.polygon:
                rx = vx * cos_a - vy * sin_a
                ry = vx * sin_a + vy * cos_a
                rx *= transform.scale
                ry *= transform.scale
                world_vertices.append((transform.x + rx, transform.y + ry))

        elif body and body.body: # Ensure pymunk body exists
            # Use physics shape
            # PhysicsBody wraps a single logical body which might have multiple shapes.
            # We check body.shape which is expected to be the primary shape or a list.
            # Assuming body.shape is a single pymunk.Shape for simplicity or primary collider.

            if body.shape:
                 world_vertices = cls._get_shape_vertices(body.body, body.shape)

        elif sprite:
            # Sprite Rect Fallback
            w = sprite.width * transform.scale
            h = sprite.height * transform.scale
            corners = [
                (-w / 2, -h / 2),
                (w / 2, -h / 2),
                (w / 2, h / 2),
                (-w / 2, h / 2),
            ]
            rad = math.radians(transform.rotation)
            cos_a = math.cos(rad)
            sin_a = math.sin(rad)

            for vx, vy in corners:
                rx = vx * cos_a - vy * sin_a
                ry = vx * sin_a + vy * cos_a
                world_vertices.append((transform.x + rx, transform.y + ry))

        # Fallback to simple box if nothing else
        else:
            size = 32 * transform.scale
            corners = [(-size/2, -size/2), (size/2, -size/2), (size/2, size/2), (-size/2, size/2)]
            for vx, vy in corners:
                 world_vertices.append((transform.x + vx, transform.y + vy))

        if occluder.static:
            cls._STATIC_CACHE[entity_id] = world_vertices

        return world_vertices

    @classmethod
    def _get_shape_vertices(cls, body: pymunk.Body, shape: pymunk.Shape) -> List[Tuple[float, float]]:
        verts = []
        if hasattr(shape, "get_vertices"):
             # Poly
            for v in shape.get_vertices():
                wv = body.local_to_world(v)
                verts.append((wv.x, wv.y))
        elif isinstance(shape, pymunk.Segment):
            v1 = body.local_to_world(shape.a)
            v2 = body.local_to_world(shape.b)

            # Extrude
            dx = v2.x - v1.x
            dy = v2.y - v1.y
            length = (dx * dx + dy * dy) ** 0.5
            if length > 0.001:
                nx = -dy / length
                ny = dx / length
                thickness = 2.0

                verts.append((v1.x + nx * thickness, v1.y + ny * thickness))
                verts.append((v2.x + nx * thickness, v2.y + ny * thickness))
                verts.append((v2.x - nx * thickness, v2.y - ny * thickness))
                verts.append((v1.x - nx * thickness, v1.y - ny * thickness))
        elif isinstance(shape, pymunk.Circle):
             radius = shape.radius
             unit_verts = cls.get_circle_vertices()
             local_to_world = body.local_to_world
             for ux, uy in unit_verts:
                 wv = local_to_world((ux * radius, uy * radius))
                 verts.append((wv.x, wv.y))
        return verts

    @classmethod
    def clear_cache(cls, entity_id: int):
        if entity_id in cls._STATIC_CACHE:
            del cls._STATIC_CACHE[entity_id]
        if entity_id in cls._STATIC_CACHE_KEYS:
            del cls._STATIC_CACHE_KEYS[entity_id]
