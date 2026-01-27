
import sys
import os
import gc
import weakref

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import pygame
# Initialize pygame before importing application components that might rely on it
pygame.init()

from yukkuri_game.engine.application import Application  # noqa: E402
from yukkuri_game.scenes.gameplay import GameplayScene  # noqa: E402
from yukkuri_game.scenes.main_menu import MainMenuScene  # noqa: E402

def check_memory():
    # Redirect print to a file or capture it
    log_file = open("memory_report.txt", "w", encoding="utf-8")
    
    def log(msg):
        print(msg)
        log_file.write(msg + "\n")
        log_file.flush()

    gc.disable()
    log(f"[*] GC Enabled: {gc.isenabled()}")
    log("[*] Initializing Application...")
    app = Application(headless=True)


    # 1. Start with GameplayScene
    log("[*] Creating GameplayScene...")
    scene = GameplayScene(app)
    
    # We need to manually call setup/on_enter as SceneManager usually does
    # But let's just use SceneManager to be authentic
    log("[*] Pushing GameplayScene to SceneManager...")
    app.scene_manager.push(scene)
    
    # Create a weak ref to track it
    scene_ref = weakref.ref(scene)
    
    # Run a few updates to let subscriptions happen
    log("[*] Running updates...")
    app.update(0.1)
    app.update(0.1)
    
    # 2. Switch to MainMenu (this should exit GameplayScene)
    log("[*] Switching to MainMenuScene...")
    app.scene_manager.replace(MainMenuScene(app))
    
    # Drop local reference
    del scene
    
    # Run updates to process events/cleanup if any
    log("[*] Running post-switch updates...")
    app.update(0.1)
    
    # Force GC - DISABLED to test reference counting
    log("[*] GC is NOT explicitly called. Relying on refcounting (unless triggered auto).")
    # gc.collect()
    
    # Check if scene is still alive
    obj = scene_ref()

    if obj is None:
        log("[SUCCESS] GameplayScene was collected.")
    else:
        log(f"[FAIL] GameplayScene is still alive: {obj}")
        # inspect referrers
        log("Referrers:")
        refs = gc.get_referrers(obj)
        for ref in refs:
             # Filter out the locals from get_referrers call itself if any
            if ref is refs:
                continue
            
            if isinstance(ref, dict):
                # Try to identify what object owns this dict (usually __dict__)
                found_owner = False
                for other in gc.get_referrers(ref):
                    if hasattr(other, "__dict__") and other.__dict__ is ref:
                        log(f" - dict of {type(other)}: {other}")
                        found_owner = True
                        break
                if not found_owner:
                    log(f" - dict: {list(ref.keys())[:5]}...") # only show first few keys
            elif isinstance(ref, list):
                log(f" - list (len={len(ref)})")
            elif hasattr(ref, "__name__"):
                 log(f" - {type(ref)}: {ref.__name__}")
            else:
                 log(f" - {type(ref)}")


if __name__ == "__main__":
    check_memory()
