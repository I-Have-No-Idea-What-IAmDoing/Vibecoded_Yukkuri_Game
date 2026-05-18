"""
Geometry Utilities Module.
"""

import math

import pymunk
from yukkuri_game.engine.components import Occluder, PhysicsBody, Sprite, Transform


class GeometryUtils:
    """
    Utilities for generating render geometry.
    """

    CIRCLE_OCCLUDER_SEGMENTS = 12
    _CIRCLE_CACHE: list[tuple[float, float]] | None = None

    # Cache for static vertices: entity_id -> vertices
    _STATIC_CACHE: dict[int, list[tuple[float, float]]] = {}
    # Cache key to invalidate static cache if transform changes
    _STATIC_CACHE_KEYS: dict[int, tuple[float, float, float, float]] = {}

    @classmethod
    def get_circle_vertices(cls) -> list[tuple[float, float]]:
        if cls._CIRCLE_CACHE is None:
            cls._CIRCLE_CACHE = []
            for i in range(cls.CIRCLE_OCCLUDER_SEGMENTS):
                # Reverse order for CCW in screen space (Y-down)
                angle = -2 * math.pi * i / cls.CIRCLE_OCCLUDER_SEGMENTS
                cls._CIRCLE_CACHE.append((math.cos(angle), math.sin(angle)))
        return cls._CIRCLE_CACHE

    @classmethod
    def get_occluder_vertices(
        cls,
        entity_id: int,
        transform: Transform,
        occluder: Occluder,
        sprite: Sprite | None = None,
        body: PhysicsBody | None = None,
        override_x: float | None = None,
        override_y: float | None = None,
    ) -> list[tuple[float, float]]:
        # Check cache for static objects
        if occluder.static:
            key = (transform.x, transform.y, transform.rotation, transform.scale)
            if entity_id in cls._STATIC_CACHE:
                if (
                    entity_id in cls._STATIC_CACHE_KEYS
                    and cls._STATIC_CACHE_KEYS[entity_id] == key
                ):
                    return cls._STATIC_CACHE[entity_id]
            cls._STATIC_CACHE_KEYS[entity_id] = key

        world_vertices = []
        tx = override_x if override_x is not None else transform.x
        ty = override_y if override_y is not None else transform.y

        if occluder.polygon:
            rad = math.radians(transform.rotation)
            cos_a = math.cos(rad)
            sin_a = math.sin(rad)
            for vx, vy in occluder.polygon:
                rx = vx * cos_a - vy * sin_a
                ry = vx * sin_a + vy * cos_a
                rx *= transform.scale
                ry *= transform.scale
                world_vertices.append((tx + rx, ty + ry))
        elif body and body.body:
            body_x, body_y = body.body.position
            offset_x = tx - body_x
            offset_y = ty - body_y
            raw_vertices = cls._get_shape_vertices(body.body, body.shape)
            if offset_x != 0 or offset_y != 0:
                world_vertices = [
                    (vx + offset_x, vy + offset_y) for vx, vy in raw_vertices
                ]
            else:
                world_vertices = raw_vertices
        elif sprite:
            w = sprite.width * transform.scale
            h = sprite.height * transform.scale
            corners = [
                (-w / 2, -h / 2),
                (-w / 2, h / 2),
                (w / 2, h / 2),
                (w / 2, -h / 2),
            ]
            rad = math.radians(transform.rotation)
            cos_a = math.cos(rad)
            sin_a = math.sin(rad)
            for vx, vy in corners:
                rx = vx * cos_a - vy * sin_a
                ry = vx * sin_a + vy * cos_a
                world_vertices.append((tx + rx, ty + ry))
        else:
            size = 32 * transform.scale
            corners = [
                (-size / 2, -size / 2),
                (-size / 2, size / 2),
                (size / 2, size / 2),
                (size / 2, -size / 2),
            ]
            for vx, vy in corners:
                world_vertices.append((tx + vx, ty + vy))

        if occluder.static:
            cls._STATIC_CACHE[entity_id] = world_vertices
        return world_vertices

    @classmethod
    def _get_shape_vertices(
        cls, body: pymunk.Body, shape: pymunk.Shape
    ) -> list[tuple[float, float]]:
        verts = []
        if hasattr(shape, "get_vertices"):
            raw_verts = shape.get_vertices()
            for v in reversed(raw_verts):
                wv = body.local_to_world(v)
                verts.append((wv.x, wv.y))
        elif isinstance(shape, pymunk.Segment):
            v1 = body.local_to_world(shape.a)
            v2 = body.local_to_world(shape.b)
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
    def clear_cache(cls, entity_id: int) -> None:
        if entity_id in cls._STATIC_CACHE:
            del cls._STATIC_CACHE[entity_id]
        if entity_id in cls._STATIC_CACHE_KEYS:
            del cls._STATIC_CACHE_KEYS[entity_id]
