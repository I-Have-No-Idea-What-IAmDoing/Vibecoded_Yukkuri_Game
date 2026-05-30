"""
Shared helpers for animation setup.
"""

from __future__ import annotations

from typing import Any

from ...engine.data_models import AnimationDefinition
from ...engine.components import Animator


def build_animator_from_data(
    data: Any,
    frame_count: int,
    frame_duration: float,
    loop: bool,
    default_anim: str = "idle",
) -> Animator | None:
    """
    Builds an Animator from data-driven animations or falls back to frame-based animation.

    Args:
        data: Data source that may expose an ``animations`` mapping.
        frame_count: Frame count for fallback animation construction.
        frame_duration: Duration per frame in seconds.
        loop: Whether the fallback animation should loop.
        default_anim: Preferred animation name to start with.

    Returns:
        Animator | None: A constructed Animator or None if no animations are available.
    """
    anims: dict[str, AnimationDefinition] = {}

    if hasattr(data, "animations") and data.animations:
        for name, definition in data.animations.items():
            anim_def = AnimationDefinition(
                name=definition.name,
                frames=definition.frames,
                frame_duration=definition.frame_duration,
                loop=definition.loop,
                ping_pong=definition.ping_pong,
                events=definition.events,
                image=definition.image,
                width=definition.width,
                height=definition.height,
            )
            anims[name.lower()] = anim_def

    if not anims and frame_count > 1:
        anims[default_anim] = AnimationDefinition(
            name=default_anim,
            frames=list(range(frame_count)),
            frame_duration=frame_duration,
            loop=loop,
        )

    if not anims:
        return None

    initial_anim = default_anim if default_anim in anims else next(iter(anims))

    return Animator(
        animations=anims,
        current_animation=initial_anim,
        current_frame_index=0,
        timer=0.0,
        speed=1.0,
    )
