package com.yukkuri.game.game.components;

import com.badlogic.ashley.core.Component;

public class YukkuriStatsComponent implements Component {
    public String name;
    public String typeId;
    public float health = 100.0f;
    public float maxHealth = 100.0f;
    public float hunger = 0.0f;
    public float happiness = 50.0f;
    public float energy = 100.0f;
    public float cleanliness = 100.0f;
    public float age = 0.0f;
    public String growthStage = "Baby";
    public int badges = 0;
    public float qualityScore = 0.0f;
    public float discipline = 0.0f;
}
