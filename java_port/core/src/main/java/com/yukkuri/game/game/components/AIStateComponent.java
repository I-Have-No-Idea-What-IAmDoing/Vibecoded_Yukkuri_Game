package com.yukkuri.game.game.components;

import com.badlogic.ashley.core.Component;
import java.util.Map;
import java.util.HashMap;

public class AIStateComponent implements Component {
    public String currentAction = "Idle";
    public int currentTargetId = -1;
    // Simple path as list of coordinates (x,y)
    public java.util.List<com.badlogic.gdx.math.Vector2> path;
    public float actionProgress = 0.0f;
    public Map<String, Object> stateData = new HashMap<>();
}
