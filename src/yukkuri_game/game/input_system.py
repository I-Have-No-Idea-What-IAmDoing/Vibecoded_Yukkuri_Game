import pygame
from ..engine.ecs import System, World
from .components import Transform, Selectable

class InputSystem(System):
    """
    System responsible for handling user input related to the game world.

    Handles entity selection and placement of new entities.

    Attributes:
        yukkurrium (Yukkurrium): The game world view manager.
        placing_mode (bool): Whether the game is currently in placement mode.
        place_type (str): The type ID of the entity being placed.
        place_cost (int): The cost of the entity being placed.
        place_entity_type (str): The category of the entity ("yukkuri" or "item").
        gm (GameManager): Reference to the GameManager.
        factory (EntityFactory): Reference to the EntityFactory.
    """

    def __init__(self, yukkurrium):
        """
        Initializes the InputSystem.

        Args:
            yukkurrium: The Yukkurrium instance.
        """
        self.yukkurrium = yukkurrium
        self.placing_mode = False
        self.place_type = None
        self.place_cost = 0
        self.place_entity_type = None # "yukkuri" or "item"
        self.gm = None
        self.factory = None

    def start_placement(self, type_id: str, cost: int, entity_type: str, gm, factory) -> None:
        """
        Enters placement mode for a specific entity.

        Args:
            type_id: The ID of the entity type to place.
            cost: The cost to deduct upon placement.
            entity_type: The category ("yukkuri" or "item").
            gm: The GameManager instance.
            factory: The EntityFactory instance.
        """
        self.placing_mode = True
        self.place_type = type_id
        self.place_cost = cost
        self.place_entity_type = entity_type
        self.gm = gm
        self.factory = factory

    def update(self, world: World, dt: float) -> None:
        """
        Updates the input system.

        Does nothing each frame as this system reacts to events.

        Args:
            world: The ECS World.
            dt: Delta time.
        """
        pass

    def handle_event(self, event: pygame.event.Event, world: World, screen_w: int, screen_h: int, ui_manager=None) -> None:
        """
        Handles a single Pygame event.

        Args:
            event: The Pygame event.
            world: The ECS World.
            screen_w: The width of the screen.
            screen_h: The height of the screen.
            ui_manager: The UI manager (optional) to check for UI interaction.
        """
        self.yukkurrium.handle_input(event, screen_w, screen_h)

        if event.type == pygame.MOUSEBUTTONDOWN:
            # Check if UI is handling the event
            if ui_manager and ui_manager.get_hovering_any_element():
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
                    if not trans:
                        continue
                    # Assume 32px radius roughly
                    dist = ((trans.x - wx)**2 + (trans.y - wy)**2)**0.5

                    selectable = world.get_component(ent, Selectable)
                    if not selectable:
                        continue

                    if dist < 32:
                        selectable.selected = True
                        clicked_something = True
                    else:
                        if not pygame.key.get_pressed()[pygame.K_LSHIFT]: # Shift adds to selection
                            selectable.selected = False

                if not clicked_something:
                     # Deselect all if clicked ground
                     for ent in entities:
                         selectable = world.get_component(ent, Selectable)
                         if selectable:
                             selectable.selected = False
            elif event.button == 3: # Right Click cancels placement
                if self.placing_mode:
                    self.placing_mode = False

    def handle_placement(self, wx: float, wy: float) -> None:
        """
        Executes the placement of an entity at world coordinates.

        Deducts money and creates the entity if funds are sufficient.

        Args:
            wx: The world x-coordinate.
            wy: The world y-coordinate.
        """
        if self.gm.money >= self.place_cost:
            self.gm.money -= self.place_cost
            if self.place_entity_type == "yukkuri":
                self.factory.create_yukkuri(self.place_type, wx, wy)
            elif self.place_entity_type == "item":
                self.factory.create_item(self.place_type, wx, wy)
