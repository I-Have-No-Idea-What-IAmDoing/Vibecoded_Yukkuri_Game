from typing import List, Dict, Any, Optional

class World:
    def __init__(self, room_data: Dict[str, Any], item_definitions: List[Dict[str, Any]]) -> None:
        self.width: int = room_data['width']
        self.height: int = room_data['height']
        self.placed_items: List[Dict[str, Any]] = []
        self.item_definitions: Dict[str, Dict[str, Any]] = {item['id']: item for item in item_definitions}
        self.grid: List[List[Optional[Dict[str, Any]]]] = [[None for _ in range(self.width)] for _ in range(self.height)]
        self.inventory: List[Dict[str, Any]] = []
        self._populate_initial_inventory(room_data['initial_inventory'])

    def _populate_initial_inventory(self, inventory_ids: List[str]) -> None:
        self.inventory = [self.item_definitions[item_id] for item_id in inventory_ids]

    def is_valid_placement(self, item_def: Dict[str, Any], x: int, y: int) -> bool:
        """Checks if an item can be placed at the given grid coordinates."""
        footprint = item_def['footprint']
        # Check bounds
        if not (0 <= x < self.width and 0 <= y < self.height):
            return False
        if not (0 <= x + footprint['w'] -1 < self.width and 0 <= y + footprint['h'] -1 < self.height):
            return False

        # Check for collisions with other items
        for i in range(footprint['h']):
            for j in range(footprint['w']):
                if self.grid[y + i][x + j] is not None:
                    return False
        return True

    def place_item(self, item_def: Dict[str, Any], x: int, y: int) -> bool:
        """Places an item on the grid."""
        if self.is_valid_placement(item_def, x, y):
            placed_item: Dict[str, Any] = {
                'id': item_def['id'],
                'x': x,
                'y': y,
                'def': item_def
            }
            self.placed_items.append(placed_item)
            footprint = item_def['footprint']
            for i in range(footprint['h']):
                for j in range(footprint['w']):
                    self.grid[y + i][x + j] = placed_item
            return True
        return False
