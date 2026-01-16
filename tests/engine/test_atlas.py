import pytest
import pygame
import sys
import os

# Ensure src is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src")))

from yukkuri_game.engine.atlas import TextureAtlas

@pytest.fixture(scope="module")
def pygame_init():
    pygame.init()
    yield
    pygame.quit()

def test_atlas_packing(pygame_init):
    # Create small atlas for testing
    atlas = TextureAtlas(size=(64, 64))
    
    # Create dummy surfaces
    # 32x32 red square
    s1 = pygame.Surface((32, 32))
    s1.fill((255, 0, 0))
    
    # 32x32 blue square
    s2 = pygame.Surface((32, 32))
    s2.fill((0, 0, 255))
    
    # 32x32 green square
    s3 = pygame.Surface((32, 32))
    s3.fill((0, 255, 0))
    
    # 32x32 yellow square
    s4 = pygame.Surface((32, 32))
    s4.fill((255, 255, 0))
    
    # Pack 1
    r1 = atlas.add_image("red", s1)
    assert r1 is not None
    assert r1.width == 32 and r1.height == 32
    
    # Pack 2 (Should fit next to 1)
    r2 = atlas.add_image("blue", s2)
    assert r2 is not None
    assert r2.colliderect(r1) == False # Should not overlap
    
    # Pack 3 (Should fit below)
    r3 = atlas.add_image("green", s3)
    assert r3 is not None
    
    # Pack 4 (Should fit last slot)
    r4 = atlas.add_image("yellow", s4)
    assert r4 is not None
    
    # Pack 5 (Should fail)
    s5 = pygame.Surface((32, 32))
    r5 = atlas.add_image("fail", s5)
    assert r5 is None
    assert "fail" in atlas.failed_to_pack

def test_atlas_retrieval(pygame_init):
    atlas = TextureAtlas(size=(100, 100))
    s1 = pygame.Surface((10, 10))
    s1.fill((123, 123, 123))
    
    atlas.add_image("test", s1)
    
    retrieved = atlas.get_region("test")
    assert retrieved is not None
    assert retrieved.get_size() == (10, 10)
    assert retrieved.get_at((0,0)) == (123, 123, 123, 255)
