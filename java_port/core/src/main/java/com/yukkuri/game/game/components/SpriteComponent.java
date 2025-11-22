package com.yukkuri.game.game.components;

import com.badlogic.ashley.core.Component;

public class SpriteComponent implements Component {
    public String imageName;
    public float width;
    public float height;
    public int layer = 0;
    public boolean flipX = false;
    public boolean flipY = false;
}
