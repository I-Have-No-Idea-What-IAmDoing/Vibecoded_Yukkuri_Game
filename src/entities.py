import pygame as pg

class Yukkuri(pg.sprite.Sprite):
    def __init__(self, yukkuri_type, position):
        super().__init__()
        self.type = yukkuri_type
        self.name = "Unnamed"
        self.health = 100
        self.hunger = 0
        self.happiness = 100
        self.cleanliness = 100
        self.age = 0
        self.growth_stage = "Baby"
        self.quality_score = 0
        self.badges = []

        # Placeholder for rendering
        self.image = pg.Surface((50, 50))
        self.image.fill("green")
        self.rect = self.image.get_rect(center=position)

    def update(self):
        # This will be driven by the AI engine later
        pass

    def calculate_quality_score(self):
        """Calculates the Yukkuri's quality score based on its stats and badges."""
        base_score = (self.health + self.happiness + self.cleanliness) / 3
        badge_bonus = len(self.badges) * 10 # 10 points per badge
        self.quality_score = int(base_score + badge_bonus)
        return self.quality_score

    def get_state(self):
        self.calculate_quality_score() # Ensure score is up-to-date
        return {
            "type": self.type,
            "name": self.name,
            "health": self.health,
            "hunger": self.hunger,
            "happiness": self.happiness,
            "cleanliness": self.cleanliness,
            "age": self.age,
            "growth_stage": self.growth_stage,
            "quality_score": self.quality_score,
            "badges": self.badges,
            "position": self.rect.center,
        }

class Item(pg.sprite.Sprite):
    def __init__(self, item_type, position):
        super().__init__()
        self.type = item_type

        # Placeholder for rendering
        self.image = pg.Surface((30, 30))
        self.image.fill("blue")
        self.rect = self.image.get_rect(center=position)

    def get_state(self):
        return {
            "type": self.type,
            "position": self.rect.center,
        }
