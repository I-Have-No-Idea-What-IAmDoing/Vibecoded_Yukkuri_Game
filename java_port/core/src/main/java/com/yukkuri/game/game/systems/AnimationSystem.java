package com.yukkuri.game.game.systems;

import com.badlogic.ashley.core.ComponentMapper;
import com.badlogic.ashley.core.Entity;
import com.badlogic.ashley.core.Family;
import com.badlogic.ashley.systems.IteratingSystem;
import com.yukkuri.game.engine.data.AnimationDefinition;
import com.yukkuri.game.game.components.AnimatorComponent;
import com.yukkuri.game.game.components.SpriteComponent;
import com.yukkuri.game.engine.ResourceManager;
import com.yukkuri.game.engine.ServiceLocator;

public class AnimationSystem extends IteratingSystem {
    private ComponentMapper<AnimatorComponent> am = ComponentMapper.getFor(AnimatorComponent.class);
    private ComponentMapper<SpriteComponent> sm = ComponentMapper.getFor(SpriteComponent.class);
    private ResourceManager resourceManager;

    public AnimationSystem() {
        super(Family.all(AnimatorComponent.class, SpriteComponent.class).get());
        resourceManager = ServiceLocator.get(ResourceManager.class);
    }

    @Override
    protected void processEntity(Entity entity, float deltaTime) {
        AnimatorComponent animator = am.get(entity);
        SpriteComponent sprite = sm.get(entity);

        if (animator.animations == null || !animator.animations.containsKey(animator.currentAnimation)) {
            return;
        }

        com.yukkuri.game.engine.data.AnimationDefinition animDef = animator.animations.get(animator.currentAnimation);

        animator.timer += deltaTime * animator.speed;

        if (animator.timer >= animDef.frame_duration) {
            animator.timer = 0;

            if (animDef.ping_pong) {
                if (animator.forward) {
                     animator.currentFrameIndex++;
                     if (animator.currentFrameIndex >= animDef.frames.size()) {
                         animator.currentFrameIndex = animDef.frames.size() - 2;
                         animator.forward = false;
                     }
                } else {
                     animator.currentFrameIndex--;
                     if (animator.currentFrameIndex < 0) {
                         animator.currentFrameIndex = 1;
                         animator.forward = true;
                     }
                }
            } else {
                 animator.currentFrameIndex++;
                 if (animator.currentFrameIndex >= animDef.frames.size()) {
                     if (animDef.loop) {
                         animator.currentFrameIndex = 0;
                     } else {
                         animator.currentFrameIndex = animDef.frames.size() - 1;
                         animator.finished = true;
                     }
                 }
            }
        }

        // Update sprite image if needed (assuming spritesheet or changing texture)
        // For this port, assuming simple frame index mapping to something, but
        // the original data just has frame indices. The python code likely maps these to regions.
        // Here we might just switch textures if "image" is overridden in animDef
        // But the original python code seems to assume a sprite sheet or a list of images.
        // Let's assume for now we just handle the logic.

        if (animDef.image != null) {
            sprite.imageName = animDef.image;
        }
    }
}
