from src.entities.yukkuri import Yukkuri
from src.entities.item import Item
import random

class Yukkurrium:
    def __init__(self, width, height, data_loader):
        self.width = width
        self.height = height
        self.data_loader = data_loader
        self.yukkuris = []
        self.items = []
        self.money = 1000
        self.time_scale = 1.0

    def spawn_yukkuri(self, type_name, x=None, y=None):
        type_data = self.data_loader.get_yukkuri_type(type_name)
        if not type_data:
            print(f"Unknown Yukkuri type: {type_name}")
            return

        if x is None: x = random.randint(50, self.width - 50)
        if y is None: y = random.randint(50, self.height - 50)

        new_yukkuri = Yukkuri(type_data, x, y)
        self.yukkuris.append(new_yukkuri)
        return new_yukkuri

    def place_item(self, item_key, x, y):
        item_data = self.data_loader.get_item_type(item_key)
        if not item_data:
            print(f"Unknown Item type: {item_key}")
            return

        cost = item_data.get('cost', 0)
        if self.money >= cost:
            self.money -= cost
            new_item = Item(item_key, item_data, x, y)
            self.items.append(new_item)
            return new_item
        else:
            print("Not enough money")
            return None

    def force_place_item(self, item_key, x, y):
        # Places item without cost check, useful for loading
        item_data = self.data_loader.get_item_type(item_key)
        if not item_data:
            print(f"Unknown Item type: {item_key}")
            return

        new_item = Item(item_key, item_data, x, y)
        self.items.append(new_item)
        return new_item

    def remove_yukkuri(self, yukkuri):
        if yukkuri in self.yukkuris:
            self.yukkuris.remove(yukkuri)

    def remove_item(self, item):
        if item in self.items:
            self.items.remove(item)

    def update(self, dt):
        for y in self.yukkuris:
            y.update(dt)

            # Boundary checks
            y.position[0] = max(0, min(y.position[0], self.width))
            y.position[1] = max(0, min(y.position[1], self.height))

    def sell_yukkuri(self, yukkuri):
        value = int(yukkuri.quality_score * 10) # Simple valuation formula
        self.money += value
        self.remove_yukkuri(yukkuri)
        return value
