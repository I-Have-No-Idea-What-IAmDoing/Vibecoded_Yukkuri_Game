package com.yukkuri.game.engine.data;

import java.util.HashMap;
import java.util.Map;

public class YukkuriType {
    public String name;
    public String image;
    public int width;
    public int height;
    public int max_health;
    public int base_happiness;
    public int cost = 100;
    public Map<String, AnimationDefinition> animations = new HashMap<>();
}
