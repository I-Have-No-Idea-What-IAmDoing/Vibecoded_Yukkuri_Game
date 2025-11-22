package com.yukkuri.game.engine.data;

import java.util.ArrayList;
import java.util.List;

public class AIAction {
    public double weight;
    public ActionEffect effects;
    public List<ActionConsideration> considerations = new ArrayList<>();
}
