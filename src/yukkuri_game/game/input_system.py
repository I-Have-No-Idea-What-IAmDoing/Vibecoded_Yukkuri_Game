import pygame
from ..engine.ecs import System, World
from .components import Transform, Selectable

class InputSystem(System):
    def __init__(self, yukkurrium):
        self.yukkurrium = yukkurrium
        self.placing_mode = False
        self.place_type = None
        self.place_cost = 0
        self.place_entity_type = None # "yukkuri" or "item"
        self.gm = None
        self.factory = None

    def start_placement(self, type_id, cost, entity_type, gm, factory):
        self.placing_mode = True
        self.place_type = type_id
        self.place_cost = cost
        self.place_entity_type = entity_type
        self.gm = gm
        self.factory = factory

    def update(self, world: World, dt: float):
        pass

    def handle_event(self, event, world: World, screen_w, screen_h, ui_consumed=False):
        self.yukkurrium.handle_input(event, screen_w, screen_h)

        if event.type == pygame.MOUSEBUTTONDOWN:
            if ui_consumed:
                return

            if event.button == 1: # Left Click
                mx, my = event.pos
                wx, wy = self.yukkurrium.screen_to_world(mx, my, screen_w, screen_h)

                if self.placing_mode:
                    self.handle_placement(wx, wy)
                    # One time placement? Or continuous? Let's do one time.
                    self.placing_mode = False
                    return

                # Check clicks on entities
                # Simple point check for MVP
                entities = world.get_entities_with(Transform, Selectable)
                clicked_something = False

                for ent in entities:
                    trans = world.get_component(ent, Transform)
                    # Assume 32px radius roughly
                    dist = ((trans.x - wx)**2 + (trans.y - wy)**2)**0.5

                    selectable = world.get_component(ent, Selectable)
                    if dist < 32:
                        selectable.selected = True
                        clicked_something = True
                    else:
                        if not pygame.key.get_pressed()[pygame.K_LSHIFT]: # Shift adds to selection
                            selectable.selected = False

                if not clicked_something:
                     # Deselect all if clicked ground
                     for ent in entities:
                         world.get_component(ent, Selectable).selected = False
            elif event.button == 3: # Right Click cancels placement
                if self.placing_mode:
                    self.placing_mode = False

    def handle_placement(self, wx, wy):
        if self.gm.money >= self.place_cost:
            self.gm.money -= self.place_cost
            if self.place_entity_type == "yukkuri":
                self.factory.create_yukkuri(self.place_type, wx, wy)
            elif self.place_entity_type == "item":
                self.factory.create_item(self.place_type, wx, wy)
