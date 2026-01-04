
try:
    import pygame
    import pygame_light2d as pl2d
    from pygame_light2d import LightingEngine

    pygame.init()
    # Create a dummy window for context
    screen = pygame.display.set_mode((100, 100))

    le = LightingEngine(screen_res=(100, 100), native_res=(100, 100), lightmap_res=(50, 50))
    print("LightingEngine methods:")
    for method in dir(le):
        if not method.startswith("__"):
            print(method)

    # Check if we can create a texture and update it
    surf = pygame.Surface((100, 100))
    tex = le.surface_to_texture(surf)
    print("\nTexture methods:")
    for method in dir(tex):
        if not method.startswith("__"):
            print(method)

except Exception as e:
    print(e)
