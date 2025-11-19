"""
UI rendering logic for the Pygame adapter.
"""
import pygame

from game.core.state.game_state import GameState
from game.core.localization.localization import Localization
from game.core.ecs.components import Position, Needs, Blackboard

GRID_COLOR = (200, 210, 240)
GRID_CELL_SIZE = 40
INVENTORY_PANEL_HEIGHT = 60
INVENTORY_ITEM_SIZE = 40


def draw_game(screen: pygame.Surface, font: pygame.font.Font,
              game_state: GameState, localization: Localization,
              selected_item: str, mouse_pos: tuple[int, int]):
    """Draws all the game elements on the screen."""
    screen.fill((230, 240, 255))

    # --- Draw Grid ---
    for x in range(0, game_state.grid.width * GRID_CELL_SIZE, GRID_CELL_SIZE):
        pygame.draw.line(screen, GRID_COLOR, (x, 0), (x, game_state.grid.height * GRID_CELL_SIZE))
    for y in range(0, game_state.grid.height * GRID_CELL_SIZE, GRID_CELL_SIZE):
        pygame.draw.line(screen, GRID_COLOR, (0, y), (game_state.grid.width * GRID_CELL_SIZE, y))

    # --- Draw Placed Items (visual placeholder) ---
    for y in range(game_state.grid.height):
        for x in range(game_state.grid.width):
            if game_state.grid._grid[y][x] is not None:
                rect = pygame.Rect(x * GRID_CELL_SIZE, y * GRID_CELL_SIZE, GRID_CELL_SIZE, GRID_CELL_SIZE)
                pygame.draw.rect(screen, (100, 100, 150), rect)


    # --- Draw Yukkuris and their info ---
    for entity in game_state.entities:
        if not entity.has_component(Position) or not entity.has_component(Needs) or not entity.has_component(Blackboard):
            continue
        pos = entity.get_component(Position)
        pygame.draw.circle(screen, (255, 180, 180), (int(pos.x), int(pos.y)), 20)

        needs = entity.get_component(Needs)
        blackboard = entity.get_component(Blackboard)
        yukkuri_id = blackboard.data.get("yukkuri_id", "akari")
        yukkuri_data = game_state.game_data.yukkuris[yukkuri_id]

        name_text = localization.get(yukkuri_data["display_name_key"], "Unknown")
        action_text = f"Action: {blackboard.data.get('current_action', 'idle')}"
        hunger_text = f"Hunger: {needs.values.get('hunger', 0):.2f}"
        energy_text = f"Energy: {needs.values.get('energy', 0):.2f}"

        screen.blit(font.render(name_text, True, (0, 0, 0)), (pos.x + 30, pos.y - 40))
        screen.blit(font.render(action_text, True, (0, 0, 0)), (pos.x + 30, pos.y - 20))
        screen.blit(font.render(hunger_text, True, (0, 0, 0)), (pos.x + 30, pos.y))
        screen.blit(font.render(energy_text, True, (0, 0, 0)), (pos.x + 30, pos.y + 20))


    # --- Draw Inventory Panel ---
    panel_rect = pygame.Rect(0, screen.get_height() - INVENTORY_PANEL_HEIGHT,
                             screen.get_width(), INVENTORY_PANEL_HEIGHT)
    pygame.draw.rect(screen, (200, 200, 200), panel_rect)

    for i, item_id in enumerate(game_state.inventory):
        item_rect = pygame.Rect(10 + i * (INVENTORY_ITEM_SIZE + 10),
                                screen.get_height() - INVENTORY_PANEL_HEIGHT + 10,
                                INVENTORY_ITEM_SIZE, INVENTORY_ITEM_SIZE)
        pygame.draw.rect(screen, (150, 150, 150), item_rect)
        item_name = localization.get(game_state.game_data.items[item_id]["display_name_key"])
        text = font.render(item_name[0], True, (0,0,0))
        screen.blit(text, (item_rect.x + 5, item_rect.y + 5))


    # --- Draw Selected Item Ghost ---
    if selected_item:
        item_data = game_state.game_data.items[selected_item]
        w = item_data["size"]["w"] * GRID_CELL_SIZE
        h = item_data["size"]["h"] * GRID_CELL_SIZE

        grid_x = (mouse_pos[0] // GRID_CELL_SIZE)
        grid_y = (mouse_pos[1] // GRID_CELL_SIZE)
        ghost_rect_topleft = (grid_x * GRID_CELL_SIZE, grid_y * GRID_CELL_SIZE)

        can_place = game_state.grid.can_place(grid_x, grid_y, item_data["size"]["w"], item_data["size"]["h"])
        color = (0, 255, 0, 128) if can_place else (255, 0, 0, 128)

        s = pygame.Surface((w, h), pygame.SRCALPHA)
        s.fill(color)
        screen.blit(s, ghost_rect_topleft)
