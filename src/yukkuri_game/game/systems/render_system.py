"""
Render System Module.
"""

import pygame
from loguru import logger
from pygame_light2d import LightingEngine
from typing import Optional

from ...engine.ecs import System, World
from ...engine.resource_manager import ResourceManager
from ..camera import Camera
from .render_system_new import NewRenderSystem

# Re-exporting NewRenderSystem as RenderSystem for compatibility
class RenderSystem(NewRenderSystem):
    pass
