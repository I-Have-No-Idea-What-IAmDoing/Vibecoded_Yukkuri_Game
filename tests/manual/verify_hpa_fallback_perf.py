
import time
import statistics
from yukkuri_game.game.ai.navigation_service import NavigationService, ObstacleType
from yukkuri_game.game.ai.navigation_constants import TraversalCapability


import time
import statistics
from yukkuri_game.game.ai.navigation_service import NavigationService, ObstacleType
from yukkuri_game.game.ai.navigation_constants import TraversalCapability

def run_benchmark():
    """
    Benchmarks HPA* performance on a large maze.
    
    Scenario:
    - 400x400 Grid (10000x10000 pixels).
    - Pattern: A series of vertical High Walls with gaps (Maze-like).
    - Scenario 1 (Baseline): Walk on Clean Maze. HPA should work.
    - Scenario 2 (Bug): Fly on Maze filled with Low Obstacles (Rubble).
      - Rubble blocks Walk, so HPA Graph (built for Walk) has no connections.
      - Fly ignores Rubble, but has to navigate High Walls.
      - Since HPA Graph is broken, it falls back to Global A* on the 400x400 maze.
      - Global A* on a text-book maze is worst-case for A*.
    """
    print("Initializing Maze Benchmark (10000x10000)...")
    width, height = 10000, 10000
    nav = NavigationService(width, height, grid_step_size=25, deterministic_mode=True)
    # Grid: 400x400.
    
    start_pos = (50.0, 50.0) # Top Left
    end_pos = (9950.0, 50.0) # Top Right
    
    # helper to build high wall maze
    def build_maze(nav):
        # Create vertical walls every 500 pixels (20 cells)
        # Gaps alternating top/bottom
        for x in range(500, width, 500):
            gap_is_top = (x // 500) % 2 == 0
            
            if gap_is_top:
                # Wall from bottom to top-gap
                nav.update_obstacle_rect(x, 200, 50, height-200, walkable=False, obstacle_type=ObstacleType.HIGH)
            else:
                # Wall from top to bottom-gap
                nav.update_obstacle_rect(x, 0, 50, height-200, walkable=False, obstacle_type=ObstacleType.HIGH)
                
    # --- Scenario 1: Clean Maze (Walking) ---
    print("\n--- Scenario 1: Walking on Clean Maze (HPA Expected) ---")
    build_maze(nav)
    nav.update(0) # Build Graph
    
    times_walk = []
    for _ in range(5):
        t0 = time.perf_counter()
        path = nav.find_path(start_pos, end_pos, can_fly=False)
        dt = time.perf_counter() - t0
        times_walk.append(dt)
        print(f"  Run {_}: {dt*1000:.2f} ms")
        assert len(path) > 0, "Walk path not found"
        
    avg_walk = statistics.mean(times_walk)
    
    # --- Scenario 2: Rubble Maze (Flying) ---
    print("\n--- Scenario 2: Flying over Rubble Maze (Fallback Expected) ---")
    
    # Reset and Rebuild Maze + Rubble
    nav.reset()
    build_maze(nav) # Same walls
    
    # Add Rubble (Low Obstacles) EVERYWHERE in the open space.
    # This ensures Walk Graph is destroyed (no nodes/edges).
    # But Fly can still move.
    
    # We can just fil the whole map with Low Obstacles, then overwrite High obstacles.
    # Actually, simpler: fill whole map with Low. Then add High Walls on top.
    # (update_obstacle_rect handles overlap by latest update? No, it paints usage grid).
    # Correct order: Fill Low, Add High.
    
    print("  Filling world with rubble...")
    # Fill background with Low
    nav.update_obstacle_rect(0, 0, width, height, walkable=False, obstacle_type=ObstacleType.LOW)
    
    # Re-add High Walls (because we just overwrote them with Low? Actually update_obstacle just sets flags.
    # HIGH = 1 (blocks all). LOW = 0 (blocks walk).
    # If we paint LOW, it sets block_mask = WALK.
    # If we paint HIGH, it sets block_mask = WALK | FLY.
    # So we need to re-paint High walls to ensure they block Fly.
    build_maze(nav)
    
    print("  Rebuilding graph (this might take a moment)...")
    nav.update(0)
    
    times_fly = []
    for _ in range(5):
        t0 = time.perf_counter()
        path = nav.find_path(start_pos, end_pos, can_fly=True)
        dt = time.perf_counter() - t0
        times_fly.append(dt)
        print(f"  Run {_}: {dt*1000:.2f} ms")
        assert len(path) > 0, "Fly path not found"
        
    avg_fly = statistics.mean(times_fly)
    ratio = avg_fly / avg_walk if avg_walk > 0 else 0

    with open("benchmark_results.txt", "w") as f:
        f.write(f"Average Walk Time (HPA Maze): {avg_walk*1000:.2f} ms\n")
        f.write(f"Average Fly Time (Fallback Maze): {avg_fly*1000:.2f} ms\n")
        f.write(f"Ratio (Fly/Walk): {ratio:.2f}x\n")
        
        if ratio > 2.0:
            f.write("CONCLUSION: Flying is significantly slower (>2x). Fallback confirmed.\n")
        else:
            f.write("CONCLUSION: Performance is similar. HPA might be working or Walk is also slow.\n")
            
    print("Benchmark complete. Results written to benchmark_results.txt")

if __name__ == "__main__":
    run_benchmark()




if __name__ == "__main__":
    run_benchmark()
