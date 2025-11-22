package com.yukkuri.game.game.components;

import com.badlogic.ashley.core.Component;
import com.yukkuri.game.engine.data.AnimationDefinition;
import java.util.Map;

public class AnimatorComponent implements Component {
    public Map<String, AnimationDefinition> animations;
    public String currentAnimation = "default";
    public int currentFrameIndex = 0;
    public float timer = 0.0f;
    public boolean finished = false;
    public float speed = 1.0f;
    public String nextAnimation = null;
    public boolean forward = true;
}
