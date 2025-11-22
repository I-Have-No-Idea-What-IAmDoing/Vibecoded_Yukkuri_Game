package com.yukkuri.game.game.ai;

import com.yukkuri.game.engine.data.ActionConsideration;
import com.yukkuri.game.game.components.YukkuriStatsComponent;

import java.util.Map;

public class UtilityAI {

    public static double evaluateAction(com.yukkuri.game.engine.data.AIAction action, YukkuriStatsComponent stats) {
        double score = action.weight;

        for (ActionConsideration consideration : action.considerations) {
            double inputValue = getInputValue(consideration.input, stats);
            double utility = evaluateCurve(consideration.curve, inputValue, consideration.params);
            score *= utility;
        }

        return score;
    }

    private static double getInputValue(String input, YukkuriStatsComponent stats) {
        switch (input) {
            case "hunger": return stats.hunger;
            case "happiness": return stats.happiness;
            case "energy": return stats.energy;
            case "cleanliness": return stats.cleanliness;
            case "discipline": return stats.discipline;
            default: return 0.0;
        }
    }

    private static double evaluateCurve(String curve, double x, Map<String, Double> params) {
        // Normalize x to 0-1 range based on assumed stat range 0-100
        double t = Math.max(0.0, Math.min(1.0, x / 100.0));

        // Use params (m, b, k, etc) if available, or defaults
        double m = params.getOrDefault("m", 1.0);
        double b = params.getOrDefault("b", 0.0);
        double k = params.getOrDefault("k", 1.0);

        switch (curve) {
            case "linear":
                return Math.max(0.0, Math.min(1.0, m * t + b));
            case "inverse_linear":
                return Math.max(0.0, Math.min(1.0, 1.0 - (m * t + b)));
            case "sigmoid":
                // simple sigmoid approx
                return 1.0 / (1.0 + Math.exp(-k * (t - 0.5)));
            default:
                return 0.5;
        }
    }
}
