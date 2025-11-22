package com.yukkuri.game;

import com.badlogic.gdx.Game;
import com.badlogic.gdx.Gdx;
import com.badlogic.gdx.graphics.GL20;
import com.yukkuri.game.engine.AudioManager;
import com.yukkuri.game.engine.EventBus;
import com.yukkuri.game.engine.ResourceManager;
import com.yukkuri.game.engine.ServiceLocator;
import com.yukkuri.game.screens.GameScreen;

public class YukkuriGame extends Game {
    @Override
    public void create() {
        Gdx.app.log("YukkuriGame", "Initializing Engine...");

        // Initialize Core Services
        EventBus eventBus = new EventBus();
        ServiceLocator.register(EventBus.class, eventBus);

        ResourceManager resourceManager = new ResourceManager();
        resourceManager.loadAllData();
        resourceManager.finishLoadingAssets(); // Block until assets are loaded
        ServiceLocator.register(ResourceManager.class, resourceManager);

        AudioManager audioManager = new AudioManager();
        ServiceLocator.register(AudioManager.class, audioManager);

        Gdx.app.log("YukkuriGame", "Engine Initialized. Starting Game...");

        setScreen(new GameScreen());
    }

    @Override
    public void render() {
        Gdx.gl.glClearColor(0.2f, 0.2f, 0.2f, 1);
        Gdx.gl.glClear(GL20.GL_COLOR_BUFFER_BIT);
        super.render();
    }

    @Override
    public void dispose() {
        super.dispose();
        ServiceLocator.get(ResourceManager.class).dispose();
        ServiceLocator.get(AudioManager.class).dispose();
    }
}
