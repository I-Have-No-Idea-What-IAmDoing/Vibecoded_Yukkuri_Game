import pygame
print(f"Pygame version: {pygame.version.ver}")
try:
    print(f"Surface: {pygame.Surface}")
    print(f"Event: {pygame.event.Event}")
except AttributeError as e:
    print(f"Error: {e}")
