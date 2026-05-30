"""
Render Passes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .background_pass import BackgroundPass
from .culling_pass import CullingPass
from .shadow_pass import ShadowPass
from .sprite_pass import SpritePass
from .light_pass import LightPass
from .occluder_pass import OccluderPass
from .ui_pass import UIPass

if TYPE_CHECKING:
    from .....engine.rendering.pipeline import RenderPipeline


__all__ = [
    "BackgroundPass",
    "CullingPass",
    "ShadowPass",
    "SpritePass",
    "LightPass",
    "OccluderPass",
    "UIPass",
    "create_gameplay_pipeline",
]


def create_gameplay_pipeline() -> "RenderPipeline":
    """Creates the gameplay render pipeline using game-specific passes.

    This pipeline includes the game-layer UIPass which renders the
    placement preview ghost sprite and other gameplay UI overlays,
    replacing the minimal engine-level UIPass that only draws
    floating text.

    Returns:
        RenderPipeline: A fully configured pipeline for gameplay scenes.
    """
    from .....engine.rendering.pipeline import RenderPipeline

    return RenderPipeline(
        [
            CullingPass(),
            BackgroundPass(),
            ShadowPass(),
            SpritePass(),
            LightPass(),
            OccluderPass(),
            UIPass(),
        ]
    )
