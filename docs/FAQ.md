# Frequently Asked Questions (FAQ)

## Gameplay

### Q: How do I save my game?
A: You can save your game by clicking the "Save" button in the top bar of the HUD. The game state is serialized and stored in a save file.

### Q: Why are my Yukkuris unhappy?
A: Yukkuris can become unhappy for various reasons:
-   **Hunger**: Make sure they are well-fed.
-   **Stress**: Too much punishment or a crowded environment can increase stress.
-   **Environment**: A dirty environment (poop) reduces happiness. Use the Clean Tool to clean up.
-   **Boredom**: Buy toys for them to play with.

### Q: How do I earn money?
A: You can earn money by selling Yukkuris. The value of a Yukkuri depends on its stats, age, and badges. Well-raised Yukkuris sell for more.

## Troubleshooting

### Q: The game crashes on startup. What should I do?
A: Check the console output or log file for error messages. Common causes include:
-   Missing dependencies: Run `pip install -e .` again.
-   Corrupted configuration files: Delete or fix files in `data/`.
-   Incompatible Python version: Ensure you are using Python 3.11+.

### Q: I found a bug. Where do I report it?
A: Please report bugs on our GitHub Issues page. provide detailed steps to reproduce the issue.

## Development

### Q: Where can I find the game assets?
A: Game assets (images, sounds) are located in the `assets/` directory.

### Q: How do I add a new Yukkuri type?
A: You can add a new Yukkuri type by editing `data/yukkuris/types.toml`. You will also need to add the corresponding image to `assets/images/`. See [Data Driven Design](DATA_DRIVEN_DESIGN.md) for more info.

### Q: Can I run the game without a window (headless)?
A: Yes, you can run the game in headless mode for testing or server-side simulation.
```bash
python -m src.yukkuri_game.main --headless
```
See [Headless Testing](headless_testing.md) for more details.
