"""
Geometry Utilities Module.

This module provides utility functions for generating and caching render geometry,
particularly for occluders and physics shapes.
"""

import math

import pymunk
from ..components import Occluder, PhysicsBody, Sprite, Transform


class GeometryUtils:
    """
    Utilities for generating render geometry.

    Attributes:
        CIRCLE_OCCLUDER_SEGMENTS (int): Number of segments for circle approximation.
        _CIRCLE_CACHE (list[tuple[float, float]] | None): Cached unit circle vertices.
        _STATIC_CACHE (dict[int, list[tuple[float, float]]]): Cache for static occluder vertices.
        _STATIC_CACHE_KEYS (dict[int, tuple]): Keys to validate static cache (transform state).
    """

    CIRCLE_OCCLUDER_SEGMENTS = 12
    _CIRCLE_CACHE: list[tuple[float, float]] | None = None

    # Cache for static vertices: entity_id -> vertices
    _STATIC_CACHE: dict[int, list[tuple[float, float]]] = {}
    # Cache key to invalidate static cache if transform changes
    _STATIC_CACHE_KEYS: dict[int, tuple[float, float, float, float]] = {}

    @classmethod
    def get_circle_vertices(cls) -> list[tuple[float, float]]:
        """
        Returns cached unit circle vertices.

        Returns:
            list[tuple[float, float]]: List of (x, y) vertices for a unit circle.
        """
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
        """
        Calculates world-space vertices for an occluder.

        Handles polygon shapes, physics bodies, sprites, and fallback boxes.
        Supports caching for static objects.

        Args:
            entity_id (int): The entity ID.
            transform (Transform): The transform component.
            occluder (Occluder): The occluder component.
            sprite (Sprite | None): Optional sprite component for dimensions.
            body (PhysicsBody | None): Optional physics body for shape data.
            override_x (float | None): Optional override for X position (e.g. interpolated).
            override_y (float | None): Optional override for Y position.

        Returns:
            list[tuple[float, float]]: List of world-space vertices.
        """
        # Check cache for static objects
        if occluder.static:
            key = (transform.x, transform.y, transform.rotation, transform.scale)
            if entity_id in cls._STATIC_CACHE:
                if (
                    entity_id in cls._STATIC_CACHE_KEYS
                    and cls._STATIC_CACHE_KEYS[entity_id] == key
                ):
                    return cls._STATIC_CACHE[entity_id]

            # Update key
            cls._STATIC_CACHE_KEYS[entity_id] = key

        world_vertices = []

        # Use overridden coordinates if provided, else transform's
        tx = override_x if override_x is not None else transform.x
        ty = override_y if override_y is not None else transform.y

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
                world_vertices.append((tx + rx, ty + ry))

        elif body and body.body:  # Ensure pymunk body exists
            # Use physics shape
            # NOTE: Pymunk bodies are updated by physics step, so they are "current".
            # If we want to interpolate them, we need to know their velocity or prev position.
            # However, usually physics bodies are the source of truth for "current" frame.
            # But rendering might be interpolated between physics steps.
            # If we are interpolating, we should offset the vertices.

            # The vertices from _get_shape_vertices are in world space based on body.position.
            # body.position is usually the "current" physics state.
            # If override_x/y is provided, it means we want to render at a different position (interpolated).
            # We calculate the offset between desired position and body position.

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
            # Sprite Rect Fallback
            w = sprite.width * transform.scale
            h = sprite.height * transform.scale
            # CCW in Screen Space (Y-down): TL -> BL -> BR -> TR
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

        # Fallback to simple box if nothing else
        else:
            size = 32 * transform.scale
            # CCW in Screen Space
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
            # Poly
            # Pymunk vertices are CCW in Y-up.
            # Converting to Y-down screen space flips the Y axis, making them CW.
            # We must reverse them to keep CCW in screen space.

            raw_verts = shape.get_vertices()
            # Reverse for Screen Space CCW
            for v in reversed(raw_verts):
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

                # Segment logic produces CCW winding in screen space (Y-down).
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
        """
        Clears the static cache for a specific entity.

        Args:
            entity_id (int): The entity ID to clear.
        """
        if entity_id in cls._STATIC_CACHE:
            del cls._STATIC_CACHE[entity_id]
        if entity_id in cls._STATIC_CACHE_KEYS:
            del cls._STATIC_CACHE_KEYS[entity_id]
