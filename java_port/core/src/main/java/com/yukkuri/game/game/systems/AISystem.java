package com.yukkuri.game.game.systems;

import com.badlogic.ashley.core.ComponentMapper;
import com.badlogic.ashley.core.Entity;
import com.badlogic.ashley.core.Family;
import com.badlogic.ashley.systems.IntervalIteratingSystem;
import com.yukkuri.game.engine.ResourceManager;
import com.yukkuri.game.engine.ServiceLocator;
import com.yukkuri.game.engine.data.AIAction;
import com.yukkuri.game.game.ai.UtilityAI;
import com.yukkuri.game.game.components.AIStateComponent;
import com.yukkuri.game.game.components.YukkuriStatsComponent;

import java.util.Map;

public class AISystem extends IntervalIteratingSystem {
    private ComponentMapper<YukkuriStatsComponent> sm = ComponentMapper.getFor(YukkuriStatsComponent.class);
    private ComponentMapper<AIStateComponent> aim = ComponentMapper.getFor(AIStateComponent.class);
    private ResourceManager resourceManager;

    public AISystem() {
        super(Family.all(YukkuriStatsComponent.class, AIStateComponent.class).get(), 1.0f); // Run every 1 second
        resourceManager = ServiceLocator.get(ResourceManager.class);
    }

    @Override
    protected void processEntity(Entity entity) {
        YukkuriStatsComponent stats = sm.get(entity);
        AIStateComponent aiState = aim.get(entity);

        // Pick best action
        double bestScore = -1.0;
        String bestActionName = "Idle";

        Map<String, AIAction> actions = resourceManager.getAIActions();
        for (Map.Entry<String, AIAction> entry : actions.entrySet()) {
            double score = UtilityAI.evaluateAction(entry.getValue(), stats);
            if (score > bestScore) {
                bestScore = score;
                bestActionName = entry.getKey();
            }
        }

        if (!bestActionName.equals(aiState.currentAction)) {
            // Change action
            aiState.currentAction = bestActionName;
            aiState.actionProgress = 0.0f;
            // Reset target, path, etc.
        }
    }
}
