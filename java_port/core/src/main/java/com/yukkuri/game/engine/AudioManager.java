package com.yukkuri.game.engine;

import com.badlogic.gdx.Gdx;
import com.badlogic.gdx.audio.Music;
import com.badlogic.gdx.audio.Sound;

import java.util.HashMap;
import java.util.Map;

public class AudioManager {
    private final Map<String, Sound> sounds = new HashMap<>();
    private Music currentMusic;
    private float volume = 0.5f;

    public void loadSound(String name, String filepath) {
        try {
            Sound sound = Gdx.audio.newSound(Gdx.files.internal(filepath));
            sounds.put(name, sound);
        } catch (Exception e) {
            Gdx.app.error("AudioManager", "Failed to load sound: " + filepath, e);
        }
    }

    public void playSound(String name) {
        Sound sound = sounds.get(name);
        if (sound != null) {
            sound.play(volume);
        }
    }

    public void setVolume(float volume) {
        this.volume = Math.max(0f, Math.min(1f, volume));
        if (currentMusic != null) {
            currentMusic.setVolume(this.volume);
        }
    }

    public void dispose() {
        for (Sound sound : sounds.values()) {
            sound.dispose();
        }
        if (currentMusic != null) {
            currentMusic.dispose();
        }
    }
}
