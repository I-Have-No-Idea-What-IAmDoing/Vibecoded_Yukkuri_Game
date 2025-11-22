package com.yukkuri.game.screens;

import com.badlogic.ashley.core.Engine;
import com.badlogic.ashley.core.Entity;
import com.badlogic.gdx.Gdx;
import com.badlogic.gdx.Input;
import com.badlogic.gdx.ScreenAdapter;
import com.badlogic.gdx.graphics.OrthographicCamera;
import com.badlogic.gdx.graphics.g2d.SpriteBatch;
import com.badlogic.gdx.scenes.scene2d.Stage;
import com.badlogic.gdx.scenes.scene2d.ui.Label;
import com.badlogic.gdx.scenes.scene2d.ui.Skin;
import com.badlogic.gdx.scenes.scene2d.ui.Table;
import com.badlogic.gdx.utils.viewport.ScreenViewport;
import com.yukkuri.game.engine.ResourceManager;
import com.yukkuri.game.engine.ServiceLocator;
import com.yukkuri.game.engine.data.YukkuriType;
import com.yukkuri.game.game.components.*;
import com.yukkuri.game.game.systems.*;

public class GameScreen extends ScreenAdapter {
    private Engine engine;
    private SpriteBatch batch;
    private OrthographicCamera camera;
    private Stage stage;
    private Skin skin;
    private ResourceManager resourceManager;

    public GameScreen() {
        this.resourceManager = ServiceLocator.get(ResourceManager.class);

        batch = new SpriteBatch();
        camera = new OrthographicCamera();
        camera.setToOrtho(false, 1280, 720);

        engine = new Engine();
        engine.addSystem(new AISystem());
        engine.addSystem(new PhysicsSystem());
        engine.addSystem(new AnimationSystem());
        engine.addSystem(new RenderingSystem(batch, camera));

        createUI();
        createTestEntity();
    }

    private void createUI() {
        stage = new Stage(new ScreenViewport());
        Gdx.input.setInputProcessor(stage);

        // Basic skin setup - in a real game load a skin file
        skin = new Skin();
        com.badlogic.gdx.graphics.Pixmap pixmap = new com.badlogic.gdx.graphics.Pixmap(1, 1, com.badlogic.gdx.graphics.Pixmap.Format.RGBA8888);
        pixmap.setColor(com.badlogic.gdx.graphics.Color.WHITE);
        pixmap.fill();
        skin.add("white", new com.badlogic.gdx.graphics.Texture(pixmap));
        skin.add("default", new com.badlogic.gdx.graphics.g2d.BitmapFont());

        Label.LabelStyle labelStyle = new Label.LabelStyle();
        labelStyle.font = skin.getFont("default");
        skin.add("default", labelStyle);

        Table table = new Table();
        table.setFillParent(true);
        stage.addActor(table);

        Label fpsLabel = new Label("FPS: ", skin);
        table.add(fpsLabel).top().left();
        table.row();
        // table.add(new Label("Yukkuri Raising Game - Java Port", skin));
    }

    private void createTestEntity() {
        YukkuriType reimuType = resourceManager.getYukkuriType("reimu");
        if (reimuType == null) return;

        Entity entity = new Entity();

        TransformComponent transform = new TransformComponent();
        transform.x = 640;
        transform.y = 360;
        entity.add(transform);

        VelocityComponent velocity = new VelocityComponent();
        velocity.dx = 10; // Slow drift
        entity.add(velocity);

        SpriteComponent sprite = new SpriteComponent();
        sprite.imageName = reimuType.image;
        sprite.width = reimuType.width;
        sprite.height = reimuType.height;
        entity.add(sprite);

        AnimatorComponent animator = new AnimatorComponent();
        animator.animations = reimuType.animations;
        entity.add(animator);

        YukkuriStatsComponent stats = new YukkuriStatsComponent();
        stats.name = "Reimu 01";
        stats.typeId = "reimu";
        entity.add(stats);

        AIStateComponent ai = new AIStateComponent();
        entity.add(ai);

        engine.addEntity(entity);
    }

    @Override
    public void render(float delta) {
        engine.update(delta);
        stage.act(delta);
        stage.draw();

        if (Gdx.input.isKeyJustPressed(Input.Keys.ESCAPE)) {
            Gdx.app.exit();
        }
    }

    @Override
    public void resize(int width, int height) {
        stage.getViewport().update(width, height, true);
    }

    @Override
    public void dispose() {
        batch.dispose();
        stage.dispose();
        skin.dispose();
    }
}
