"""
Unit tests for the SoftwareLightingEngine.
"""

import pytest
import pygame


class TestSurfacePool:
    """Tests for the SurfacePool class."""

    @pytest.fixture
    def pygame_init(self):
        """Initialize pygame for surface tests."""
        pygame.init()
        pygame.display.set_mode((100, 100))
        yield
        pygame.quit()

    def test_acquire_creates_new_surface(self, pygame_init):
        """acquire() creates a new surface when pool is empty."""
        from yukkuri_game.game.renderer.software_lighting import SurfacePool

        pool = SurfacePool()
        surf = pool.acquire(100, 50)

        assert surf is not None
        assert surf.get_size() == (100, 50)

    def test_acquire_reuses_released_surface(self, pygame_init):
        """acquire() reuses a surface that was released."""
        from yukkuri_game.game.renderer.software_lighting import SurfacePool

        pool = SurfacePool()
        surf1 = pool.acquire(100, 50)
        pool.release(surf1)

        surf2 = pool.acquire(100, 50)
        assert surf2 is surf1  # Same object reused

    def test_release_respects_max_pool_size(self, pygame_init):
        """release() doesn't add surfaces beyond max pool size."""
        from yukkuri_game.game.renderer.software_lighting import SurfacePool

        pool = SurfacePool(max_pool_size=2)

        surfaces = [pool.acquire(100, 50) for _ in range(5)]
        for s in surfaces:
            pool.release(s)

        # Pool should only have 2 surfaces
        assert len(pool._pool.get((100, 50), [])) == 2

    def test_acquire_clears_surface(self, pygame_init):
        """acquire() clears reused surfaces."""
        from yukkuri_game.game.renderer.software_lighting import SurfacePool

        pool = SurfacePool()
        surf1 = pool.acquire(100, 50)
        surf1.fill((255, 0, 0))  # Fill with red
        pool.release(surf1)

        surf2 = pool.acquire(100, 50)
        # Check that surface was cleared (should be transparent/black)
        pixel = surf2.get_at((50, 25))
        assert pixel.a == 0 or (pixel.r == 0 and pixel.g == 0 and pixel.b == 0)


class TestSoftwareLightingEngineInit:
    """Tests for SoftwareLightingEngine initialization."""

    @pytest.fixture
    def pygame_init(self):
        """Initialize pygame for surface tests."""
        pygame.init()
        pygame.display.set_mode((100, 100))
        yield
        pygame.quit()

    def test_initialization(self, pygame_init):
        """Engine initializes with correct sizes."""
        from yukkuri_game.game.renderer.software_lighting import (
            SoftwareLightingEngine,
        )

        engine = SoftwareLightingEngine((800, 600), scale=1.0)

        assert engine.native_size == (800, 600)
        assert engine.lightmap_size == (800, 600)
        assert engine.scale == 1.0

    def test_initialization_with_scale(self, pygame_init):
        """Engine scales lightmap when scale < 1.0."""
        from yukkuri_game.game.renderer.software_lighting import (
            SoftwareLightingEngine,
        )

        engine = SoftwareLightingEngine((800, 600), scale=0.5)

        assert engine.native_size == (800, 600)
        assert engine.lightmap_size == (400, 300)

    def test_resize(self, pygame_init):
        """resize() updates native size and lightmap."""
        from yukkuri_game.game.renderer.software_lighting import (
            SoftwareLightingEngine,
        )

        engine = SoftwareLightingEngine((800, 600), scale=1.0)
        engine.resize(1024, 768)

        assert engine.native_size == (1024, 768)
        assert engine.lightmap.get_size() == (1024, 768)


class TestClear:
    """Tests for clear() method."""

    @pytest.fixture
    def pygame_init(self):
        pygame.init()
        pygame.display.set_mode((100, 100))
        yield
        pygame.quit()

    def test_clear_fills_with_ambient(self, pygame_init):
        """clear() fills lightmap with ambient color."""
        from yukkuri_game.game.renderer.software_lighting import (
            SoftwareLightingEngine,
        )

        engine = SoftwareLightingEngine((100, 100), scale=1.0)
        engine.clear((50, 100, 150))

        pixel = engine.lightmap.get_at((50, 50))
        assert pixel.r == 50
        assert pixel.g == 100
        assert pixel.b == 150

    def test_clear_resets_occluders(self, pygame_init):
        """clear() clears occluder list."""
        from yukkuri_game.game.renderer.software_lighting import (
            SoftwareLightingEngine,
        )

        engine = SoftwareLightingEngine((100, 100), scale=1.0)
        engine.add_occluder((10, 20, 10, 20), [(10, 10), (20, 10), (20, 20), (10, 20)])

        assert len(engine.occluders) == 1

        engine.clear((0, 0, 0))

        assert len(engine.occluders) == 0
        assert len(engine.grid) == 0


class TestAddOccluder:
    """Tests for add_occluder() method."""

    @pytest.fixture
    def pygame_init(self):
        pygame.init()
        pygame.display.set_mode((100, 100))
        yield
        pygame.quit()

    def test_add_occluder_stores_data(self, pygame_init):
        """add_occluder() stores aabb and vertices."""
        from yukkuri_game.game.renderer.software_lighting import (
            SoftwareLightingEngine,
        )

        engine = SoftwareLightingEngine((800, 600), scale=1.0)
        aabb = (100, 200, 100, 200)
        vertices = [(100, 100), (200, 100), (200, 200), (100, 200)]

        engine.add_occluder(aabb, vertices)

        assert len(engine.occluders) == 1
        assert engine.occluders[0] == (aabb, vertices)

    def test_add_occluder_populates_grid(self, pygame_init):
        """add_occluder() adds occluder to spatial grid."""
        from yukkuri_game.game.renderer.software_lighting import (
            SoftwareLightingEngine,
        )

        engine = SoftwareLightingEngine((800, 600), scale=1.0)
        engine.cell_size = 100

        aabb = (50, 150, 50, 150)  # Spans cells (0,0), (0,1), (1,0), (1,1)
        vertices = [(50, 50), (150, 50), (150, 150), (50, 150)]

        engine.add_occluder(aabb, vertices)

        # Should be in 4 grid cells
        assert (0, 0) in engine.grid
        assert (1, 1) in engine.grid


class TestQueryGrid:
    """Tests for _query_grid() method."""

    @pytest.fixture
    def pygame_init(self):
        pygame.init()
        pygame.display.set_mode((100, 100))
        yield
        pygame.quit()

    def test_query_grid_returns_occluders_in_range(self, pygame_init):
        """_query_grid() returns occluders within light radius."""
        from yukkuri_game.game.renderer.software_lighting import (
            SoftwareLightingEngine,
        )

        engine = SoftwareLightingEngine((800, 600), scale=1.0)
        engine.cell_size = 100

        aabb = (100, 150, 100, 150)
        vertices = [(100, 100), (150, 100), (150, 150), (100, 150)]
        engine.add_occluder(aabb, vertices)

        # Query near the occluder
        result = engine._query_grid(125, 125, 100)

        assert len(result) > 0

    def test_query_grid_ignores_far_occluders(self, pygame_init):
        """_query_grid() doesn't return occluders far away."""
        from yukkuri_game.game.renderer.software_lighting import (
            SoftwareLightingEngine,
        )

        engine = SoftwareLightingEngine((800, 600), scale=1.0)
        engine.cell_size = 100

        aabb = (700, 750, 700, 750)
        vertices = [(700, 700), (750, 700), (750, 750), (700, 750)]
        engine.add_occluder(aabb, vertices)

        # Query far from the occluder
        result = engine._query_grid(100, 100, 50)

        assert len(result) == 0


class TestGetSurface:
    """Tests for get_surface() method."""

    @pytest.fixture
    def pygame_init(self):
        pygame.init()
        pygame.display.set_mode((100, 100))
        yield
        pygame.quit()

    def test_get_surface_returns_lightmap_at_scale_1(self, pygame_init):
        """get_surface() returns lightmap directly when scale is 1.0."""
        from yukkuri_game.game.renderer.software_lighting import (
            SoftwareLightingEngine,
        )

        engine = SoftwareLightingEngine((800, 600), scale=1.0)
        result = engine.get_surface()

        assert result is engine.lightmap

    def test_get_surface_scales_at_lower_scale(self, pygame_init):
        """get_surface() scales up when scale < 1.0."""
        from yukkuri_game.game.renderer.software_lighting import (
            SoftwareLightingEngine,
        )

        engine = SoftwareLightingEngine((800, 600), scale=0.5)
        result = engine.get_surface()

        assert result.get_size() == (800, 600)


class TestGradientGeneration:
    """Tests for gradient surface generation."""

    @pytest.fixture
    def pygame_init(self):
        pygame.init()
        pygame.display.set_mode((100, 100))
        yield
        pygame.quit()

    def test_get_gradient_surface_caches(self, pygame_init):
        """_get_gradient_surface() caches generated surfaces."""
        from yukkuri_game.game.renderer.software_lighting import (
            SoftwareLightingEngine,
        )

        engine = SoftwareLightingEngine((800, 600), scale=1.0)

        surf1 = engine._get_gradient_surface(50, (255, 255, 255), 1.0)
        surf2 = engine._get_gradient_surface(50, (255, 255, 255), 1.0)

        assert surf1 is surf2  # Same cached object

    def test_get_gradient_surface_different_params(self, pygame_init):
        """Different params create different cached surfaces."""
        from yukkuri_game.game.renderer.software_lighting import (
            SoftwareLightingEngine,
        )

        engine = SoftwareLightingEngine((800, 600), scale=1.0)

        surf1 = engine._get_gradient_surface(50, (255, 255, 255), 1.0)
        surf2 = engine._get_gradient_surface(100, (255, 255, 255), 1.0)

        assert surf1 is not surf2

    def test_gradient_surface_correct_size(self, pygame_init):
        """Gradient surface has correct size (radius * 2)."""
        from yukkuri_game.game.renderer.software_lighting import (
            SoftwareLightingEngine,
        )

        engine = SoftwareLightingEngine((800, 600), scale=1.0)

        surf = engine._get_gradient_surface(75, (255, 255, 255), 1.0)

        assert surf.get_size() == (150, 150)


class TestRenderLight:
    """Tests for render_light() method."""

    @pytest.fixture
    def pygame_init(self):
        pygame.init()
        pygame.display.set_mode((100, 100))
        yield
        pygame.quit()

    def test_render_light_modifies_lightmap(self, pygame_init):
        """render_light() adds light to the lightmap."""
        from yukkuri_game.game.renderer.software_lighting import (
            SoftwareLightingEngine,
        )

        engine = SoftwareLightingEngine((200, 200), scale=1.0)
        engine.clear((0, 0, 0))

        engine.render_light(
            position=(100, 100),
            radius=50,
            color=(255, 255, 255),
            intensity=1.0,
            soft_shadows=False,
        )

        # Center should be lit
        pixel = engine.lightmap.get_at((100, 100))
        assert pixel.r > 0 or pixel.g > 0 or pixel.b > 0

    def test_render_light_culls_offscreen(self, pygame_init):
        """render_light() culls lights fully offscreen."""
        from yukkuri_game.game.renderer.software_lighting import (
            SoftwareLightingEngine,
        )

        engine = SoftwareLightingEngine((200, 200), scale=1.0)
        engine.clear((50, 50, 50))

        # Light far offscreen
        engine.render_light(
            position=(1000, 1000),
            radius=50,
            color=(255, 255, 255),
            intensity=1.0,
        )

        # Lightmap should still be ambient color
        pixel = engine.lightmap.get_at((100, 100))
        assert pixel.r == 50
        assert pixel.g == 50
        assert pixel.b == 50

    def test_static_light_caching(self, pygame_init):
        """Static lights are cached for reuse."""
        from yukkuri_game.game.renderer.software_lighting import (
            SoftwareLightingEngine,
        )

        engine = SoftwareLightingEngine((200, 200), scale=1.0)
        engine.clear((0, 0, 0))

        # Render static light
        engine.render_light(
            position=(100, 100),
            radius=50,
            color=(255, 255, 255),
            intensity=1.0,
            static=True,
            entity_id=42,
        )

        assert 42 in engine.static_light_cache

    def test_static_light_cache_reused(self, pygame_init):
        """Static light cache is reused on subsequent renders."""
        from yukkuri_game.game.renderer.software_lighting import (
            SoftwareLightingEngine,
        )

        engine = SoftwareLightingEngine((200, 200), scale=1.0)
        engine.clear((0, 0, 0))

        # First render (creates cache)
        engine.render_light(
            position=(100, 100),
            radius=50,
            color=(255, 255, 255),
            intensity=1.0,
            static=True,
            entity_id=42,
        )

        cached_surf, cached_key = engine.static_light_cache[42]

        engine.clear((0, 0, 0))

        # Second render (should use cache)
        engine.render_light(
            position=(100, 100),
            radius=50,
            color=(255, 255, 255),
            intensity=1.0,
            static=True,
            entity_id=42,
        )

        # Cache entry should still be the same
        assert engine.static_light_cache[42][0] is cached_surf
