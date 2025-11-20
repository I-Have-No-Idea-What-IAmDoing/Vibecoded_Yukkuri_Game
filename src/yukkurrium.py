import pygame as pg
from .entities import Yukkuri, Item

class Yukkurrium:
    def __init__(self):
        self.yukkuris = pg.sprite.Group()
        self.items = pg.sprite.Group()

    def add_yukkuri(self, yukkuri_type, position):
        yukkuri = Yukkuri(yukkuri_type, position)
        self.yukkuris.add(yukkuri)

    def add_item(self, item_type, position):
        item = Item(item_type, position)
        self.items.add(item)

    def remove_yukkuri(self, yukkuri):
        self.yukkuris.remove(yukkuri)

    def remove_item(self, item):
        self.items.remove(item)

    def update(self):
        self.yukkuris.update()
        self.items.update()

    def draw(self, surface):
        self.yukkuris.draw(surface)
        self.items.draw(surface)

    def get_state(self):
        return {
            "yukkuris": [y.get_state() for y in self.yukkuris],
            "items": [i.get_state() for i in self.items],
        }
