package com.yukkuri.game.game.systems;

import com.badlogic.ashley.core.Entity;
import com.badlogic.ashley.core.Family;
import com.badlogic.ashley.systems.IteratingSystem;
import com.badlogic.gdx.graphics.OrthographicCamera;
import com.badlogic.gdx.graphics.Texture;
import com.badlogic.gdx.graphics.g2d.SpriteBatch;
import com.badlogic.gdx.graphics.g2d.TextureRegion;
import com.badlogic.gdx.utils.ScreenUtils;
import com.yukkuri.game.engine.ServiceLocator;
import com.yukkuri.game.engine.ResourceManager;
import com.yukkuri.game.game.components.*;

public class RenderingSystem extends IteratingSystem {
    private SpriteBatch batch;
    private OrthographicCamera camera;
    private ResourceManager resourceManager;

    public RenderingSystem(SpriteBatch batch, OrthographicCamera camera) {
        super(Family.all(TransformComponent.class, SpriteComponent.class).get());
        this.batch = batch;
        this.camera = camera;
        this.resourceManager = ServiceLocator.get(ResourceManager.class);
    }

    @Override
    public void update(float deltaTime) {
        ScreenUtils.clear(0, 0, 0, 1);
        camera.update();
        batch.setProjectionMatrix(camera.combined);
        batch.begin();
        super.update(deltaTime);
        batch.end();
    }

    @Override
    protected void processEntity(Entity entity, float deltaTime) {
        TransformComponent transform = entity.getComponent(TransformComponent.class);
        SpriteComponent sprite = entity.getComponent(SpriteComponent.class);

        Texture texture = resourceManager.getTexture(sprite.imageName);
        if (texture != null) {
             float width = sprite.width * transform.scale;
             float height = sprite.height * transform.scale;
             float x = transform.x - width / 2;
             float y = transform.y - height / 2;

             TextureRegion region = new TextureRegion(texture);
             if (sprite.flipX) region.flip(true, false);
             if (sprite.flipY) region.flip(false, true);

             batch.draw(region, x, y, width, height);
        }
    }
}
