# Configuration

The Yukkuri Raising Game uses TOML files for configuration. These files are located in the `data/` directory.

## Files

### `config.toml`

Contains world and engine settings.

```toml
[world]
width = 3000
height = 3000
sector_size = 500.0
```

- `width`: The width of the game world in pixels (default: 3000).
- `height`: The height of the game world in pixels (default: 3000).
- `sector_size`: The size of sectors for spatial partitioning (default: 500.0).

### `rules.toml`

Contains simulation rules and constants.

```toml
[stat_decay]
hunger = 2.0
happiness = 0.5
energy = 0.5
cleanliness = 0.2
age = 1.0
```

- `hunger`: Rate at which hunger increases per second (default: 2.0).
- `happiness`: Rate at which happiness decreases per second (default: 0.5).
- `energy`: Rate at which energy decreases per second (default: 0.5).
- `cleanliness`: Rate at which cleanliness decreases per second (default: 0.2).
- `age`: Rate at which age increases per second (default: 1.0).

## Loading

The configuration is loaded at startup by the `load_config` function in `src/yukkuri_game/config.py`. It returns a `GameConfig` object containing `world` and `rules` settings.

If configuration files are missing, default values are used.
If configuration files contain invalid types, the game will fail to start with a validation error.
Partial updates are supported; missing fields in the configuration files will use default values.
