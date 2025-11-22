package com.yukkuri.game.engine.data;

import java.util.HashMap;
import java.util.Map;

public class ActionEffect {
    public String type;
    public String target_stat;
    public boolean consume = false;
    public Map<String, Double> stat_changes = new HashMap<>();
}
