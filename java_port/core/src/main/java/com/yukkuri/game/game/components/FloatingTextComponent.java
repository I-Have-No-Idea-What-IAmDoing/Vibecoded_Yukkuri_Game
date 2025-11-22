package com.yukkuri.game.game.components;

import com.badlogic.ashley.core.Component;

public class FloatingTextComponent implements Component {
    public String text;
    public float[] color = new float[]{1, 1, 1, 1}; // RGBA
    public float lifetime;
    public float maxLifetime;
    public float velocityY;
    public int size = 20;
}
