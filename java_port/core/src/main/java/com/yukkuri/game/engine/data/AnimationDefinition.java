package com.yukkuri.game.engine.data;

import java.util.List;
import java.util.Map;

public class AnimationDefinition {
    public String name;
    public List<Integer> frames;
    public double frame_duration;
    public boolean loop = true;
    public boolean ping_pong = false;
    public Map<Integer, String> events;
    public String image;
    public Integer width;
    public Integer height;
}
