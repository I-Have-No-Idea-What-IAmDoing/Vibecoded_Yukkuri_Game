package com.yukkuri.game.game.components;

import com.badlogic.ashley.core.Component;

public class ItemStatsComponent implements Component {
    public String name;
    public String typeId;
    public int cost;
    public float nutrition = 0.0f;
    public float fun = 0.0f;
    public float comfort = 0.0f;
    public boolean isPortable = false;
}
