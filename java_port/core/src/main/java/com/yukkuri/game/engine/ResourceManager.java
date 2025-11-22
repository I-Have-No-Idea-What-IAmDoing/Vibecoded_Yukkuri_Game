package com.yukkuri.game.engine;

import com.badlogic.gdx.Gdx;
import com.badlogic.gdx.assets.AssetManager;
import com.badlogic.gdx.audio.Sound;
import com.badlogic.gdx.graphics.Texture;
import com.badlogic.gdx.graphics.g2d.TextureRegion;
import com.yukkuri.game.engine.data.*;
import org.tomlj.Toml;
import org.tomlj.TomlArray;
import org.tomlj.TomlParseResult;
import org.tomlj.TomlTable;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

public class ResourceManager {
    private final AssetManager assetManager;
    private final Map<String, YukkuriType> yukkuriTypes = new HashMap<>();
    private final Map<String, ItemType> itemTypes = new HashMap<>();
    private final Map<String, AIAction> aiActions = new HashMap<>();

    public ResourceManager() {
        this.assetManager = new AssetManager();
    }

    public void loadAllData() {
        loadYukkuriTypes();
        loadItemTypes();
        loadAIActions();
    }

    public void finishLoadingAssets() {
        assetManager.finishLoading();
    }

    private void loadYukkuriTypes() {
        try {
            String tomlString = Gdx.files.internal("assets/data/yukkuris/types.toml").readString();
            TomlParseResult result = Toml.parse(tomlString);

            TomlTable yukkurisTable = result.getTable("yukkuris");
            if (yukkurisTable != null) {
                for (String key : yukkurisTable.keySet()) {
                    TomlTable typeTable = yukkurisTable.getTable(key);
                    YukkuriType type = new YukkuriType();
                    type.name = typeTable.getString("name");
                    type.image = typeTable.getString("image");
                    type.width = typeTable.getLong("width").intValue();
                    type.height = typeTable.getLong("height").intValue();
                    type.max_health = typeTable.getLong("max_health").intValue();
                    type.base_happiness = typeTable.getLong("base_happiness") != null ? typeTable.getLong("base_happiness").intValue() : 0;
                    type.cost = typeTable.getLong("cost") != null ? typeTable.getLong("cost").intValue() : 100;

                    // Animations
                    TomlTable animsTable = typeTable.getTable("animations");
                    if (animsTable != null) {
                        for (String animKey : animsTable.keySet()) {
                             TomlTable animTable = animsTable.getTable(animKey);
                             AnimationDefinition anim = new AnimationDefinition();
                             anim.name = animTable.getString("name"); // usually key or name field
                             if (anim.name == null) anim.name = animKey;

                             TomlArray framesArray = animTable.getArray("frames");
                             anim.frames = new ArrayList<>();
                             if (framesArray != null) {
                                 for (int i = 0; i < framesArray.size(); i++) {
                                     anim.frames.add((int) framesArray.getLong(i));
                                 }
                             }

                             anim.frame_duration = animTable.getDouble("frame_duration");
                             anim.loop = animTable.getBoolean("loop") != null ? animTable.getBoolean("loop") : true;
                             anim.ping_pong = animTable.getBoolean("ping_pong") != null ? animTable.getBoolean("ping_pong") : false;
                             anim.image = animTable.getString("image");
                             if (animTable.getLong("width") != null) anim.width = animTable.getLong("width").intValue();
                             if (animTable.getLong("height") != null) anim.height = animTable.getLong("height").intValue();

                             type.animations.put(animKey, anim);
                        }
                    }

                    yukkuriTypes.put(key, type);

                    // Queue asset loading
                    if (type.image != null) {
                        loadTexture("assets/images/" + type.image);
                    }
                }
            }
        } catch (Exception e) {
            Gdx.app.error("ResourceManager", "Failed to load yukkuri types", e);
        }
    }

    private void loadItemTypes() {
        try {
            String tomlString = Gdx.files.internal("assets/data/items/items.toml").readString();
            TomlParseResult result = Toml.parse(tomlString);

            TomlTable itemsTable = result.getTable("items");
            if (itemsTable != null) {
                for (String key : itemsTable.keySet()) {
                    TomlTable itemTable = itemsTable.getTable(key);
                    ItemType type = new ItemType();
                    type.name = itemTable.getString("name");
                    type.image = itemTable.getString("image");
                    type.width = itemTable.getLong("width").intValue();
                    type.height = itemTable.getLong("height").intValue();
                    type.cost = itemTable.getLong("cost").intValue();
                    type.is_portable = itemTable.getBoolean("is_portable") != null ? itemTable.getBoolean("is_portable") : false;
                    if (itemTable.getLong("nutrition") != null) type.nutrition = itemTable.getLong("nutrition").intValue();
                    if (itemTable.getLong("comfort") != null) type.comfort = itemTable.getLong("comfort").intValue();
                    if (itemTable.getLong("fun") != null) type.fun = itemTable.getLong("fun").intValue();

                    itemTypes.put(key, type);

                    if (type.image != null) {
                         loadTexture("assets/images/" + type.image);
                    }
                }
            }
        } catch (Exception e) {
            Gdx.app.error("ResourceManager", "Failed to load item types", e);
        }
    }

    private void loadAIActions() {
        try {
            String tomlString = Gdx.files.internal("assets/data/ai/actions.toml").readString();
            TomlParseResult result = Toml.parse(tomlString);

            TomlTable actionsTable = result.getTable("actions");
            if (actionsTable != null) {
                for (String key : actionsTable.keySet()) {
                    TomlTable actionTable = actionsTable.getTable(key);
                    AIAction action = new AIAction();
                    action.weight = actionTable.getDouble("weight");

                    TomlTable effectsTable = actionTable.getTable("effects");
                    if (effectsTable != null) {
                        action.effects = new ActionEffect();
                        action.effects.type = effectsTable.getString("type");
                        action.effects.target_stat = effectsTable.getString("target_stat");
                        action.effects.consume = effectsTable.getBoolean("consume") != null ? effectsTable.getBoolean("consume") : false;

                        TomlTable statChanges = effectsTable.getTable("stat_changes");
                        if (statChanges != null) {
                            for (String stat : statChanges.keySet()) {
                                action.effects.stat_changes.put(stat, statChanges.getDouble(stat));
                            }
                        }
                    }

                    TomlArray considerationsArray = actionTable.getArray("considerations");
                    if (considerationsArray != null) {
                        for (int i = 0; i < considerationsArray.size(); i++) {
                            TomlTable consTable = considerationsArray.getTable(i);
                            ActionConsideration cons = new ActionConsideration();
                            cons.name = consTable.getString("name");
                            cons.input = consTable.getString("input");
                            cons.curve = consTable.getString("curve");

                            TomlTable paramsTable = consTable.getTable("params");
                            if (paramsTable != null) {
                                for (String param : paramsTable.keySet()) {
                                    cons.params.put(param, paramsTable.getDouble(param));
                                }
                            }
                            action.considerations.add(cons);
                        }
                    }

                    aiActions.put(key, action);
                }
            }
        } catch (Exception e) {
            Gdx.app.error("ResourceManager", "Failed to load AI actions", e);
        }
    }

    private void loadTexture(String path) {
        if (!assetManager.isLoaded(path)) {
            assetManager.load(path, Texture.class);
        }
    }

    public Texture getTexture(String name) {
        String path = "assets/images/" + name;
        if (assetManager.isLoaded(path)) {
            return assetManager.get(path, Texture.class);
        }
        return null; // Or placeholder
    }

    public YukkuriType getYukkuriType(String name) {
        return yukkuriTypes.get(name);
    }

    public ItemType getItemType(String name) {
        return itemTypes.get(name);
    }

    public Map<String, AIAction> getAIActions() {
        return aiActions;
    }

    public void dispose() {
        assetManager.dispose();
    }
}
