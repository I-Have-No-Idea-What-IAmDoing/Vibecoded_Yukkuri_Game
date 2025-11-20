import py_trees
import math
import random
from py_trees.behaviour import Behaviour
from py_trees.common import Status
from ..components import Transform, PhysicsBody, Velocity
from ..yukkuri_components import AIState, ItemStats, YukkuriStats
from ..ai.pathfinding import Pathfinding

# --- Behavior Tree Leaves (Actions) ---

class Action(Behaviour):
    def __init__(self, name="Action", entity_id=None, world=None, blackboard=None):
        super().__init__(name)
        self.entity_id = entity_id
        self.world = world
        self.blackboard = blackboard

    def update(self):
        if not self.world or self.entity_id is None:
             return Status.FAILURE
        return Status.RUNNING

class MoveToTarget(Action):
    """
    Moves the entity towards the current target set in AIState or a specific coordinate.
    This implementation uses PhysicsBody if available, or direct Transform manipulation.
    """
    def __init__(self, name="Move To Target", entity_id=None, world=None, blackboard=None, speed=100.0):
        super().__init__(name, entity_id, world, blackboard)
        self.speed = speed

    def update(self):
        super().update()
        ai = self.world.get_component(self.entity_id, AIState)
        trans = self.world.get_component(self.entity_id, Transform)
        phys = self.world.get_component(self.entity_id, PhysicsBody)

        if not ai or not trans:
            return Status.FAILURE

        target_pos = None

        # Determine target position
        if ai.current_target_id != -1:
            target_trans = self.world.get_component(ai.current_target_id, Transform)
            if target_trans:
                target_pos = (target_trans.x, target_trans.y)
            else:
                # Target lost
                ai.current_target_id = -1
                return Status.FAILURE
        elif ai.state_data and "target_x" in ai.state_data and "target_y" in ai.state_data:
            target_pos = (ai.state_data["target_x"], ai.state_data["target_y"])

        if target_pos is None:
            return Status.FAILURE

        # Pathfinding
        if ai.path is None or len(ai.path) == 0:
             # Simple check to see if we need pathfinding or just straight line
             # For now, assuming pathfinding is always needed or available
             ai.path = Pathfinding.find_path((trans.x, trans.y), target_pos, 3000, 3000) # Using hardcoded world size for now or need to pass it
             if not ai.path:
                 return Status.FAILURE

        # Move along path
        if len(ai.path) > 0:
            next_point = ai.path[0]
            dx = next_point[0] - trans.x
            dy = next_point[1] - trans.y
            dist = math.hypot(dx, dy)

            # Check if we are close to the *final* target
            dist_to_final = math.hypot(target_pos[0] - trans.x, target_pos[1] - trans.y)
            # Use a threshold slightly smaller than the interaction range to ensure we are close enough to interact
            if dist_to_final < 15.0:
                ai.path = []
                return Status.SUCCESS

            if dist < 5.0: # Reached waypoint
                ai.path.pop(0)
                if not ai.path: # Reached end of path
                    return Status.SUCCESS
            else:
                # Normalize direction
                dx /= dist
                dy /= dist

                # Apply movement
                if phys:
                    # Use physics velocity
                    phys.body.velocity = (dx * self.speed, dy * self.speed)
                    # Wake up body just in case
                    phys.body.activate()
                else:
                    # Fallback to direct transform manipulation
                    # We read delta time from blackboard if available
                    dt = py_trees.blackboard.Blackboard().get("dt")
                    if dt is None:
                         dt = 0.016 # Fallback to ~60FPS

                    step = self.speed * dt
                    if step > dist:
                        trans.x = next_point[0]
                        trans.y = next_point[1]
                    else:
                        trans.x += dx * step
                        trans.y += dy * step

            return Status.RUNNING

        return Status.SUCCESS

class Wander(Action):
    def __init__(self, name="Wander", entity_id=None, world=None, blackboard=None, width=3000, height=3000):
        super().__init__(name, entity_id, world, blackboard)
        self.width = width
        self.height = height
        self.move_action = None

    def initialise(self):
        ai = self.world.get_component(self.entity_id, AIState)
        if ai:
            # Pick a random point
            tx = random.uniform(0, self.width)
            ty = random.uniform(0, self.height)
            ai.state_data = {"target_x": tx, "target_y": ty}
            ai.path = None # Reset path

        # Create a temporary MoveToTarget to handle the actual movement logic
        self.move_action = MoveToTarget(entity_id=self.entity_id, world=self.world, blackboard=self.blackboard)

    def update(self):
        if self.move_action:
            return self.move_action.update()
        return Status.FAILURE

class Interact(Action):
    def __init__(self, name="Interact", entity_id=None, world=None, blackboard=None):
        super().__init__(name, entity_id, world, blackboard)

    def update(self):
        super().update()
        ai = self.world.get_component(self.entity_id, AIState)
        trans = self.world.get_component(self.entity_id, Transform)

        if not ai or not trans:
            return Status.FAILURE

        if ai.current_target_id == -1:
            # If target lost or not set, check if we can find it again locally or fail
            return Status.FAILURE

        target_trans = self.world.get_component(ai.current_target_id, Transform)
        if not target_trans:
            # print("Interact Fail: Target trans missing")
            return Status.FAILURE

        dist = math.hypot(target_trans.x - trans.x, target_trans.y - trans.y)
        # print(f"Interact Check: Dist={dist}")
        if dist <= 30.0: # Interaction range
            # Perform Interaction Logic
            # We need to know WHAT to do. Usually defined by the "Current Action" name or similar.
            # Or we just trigger the effect.

            # This logic was previously in execute_action
            item_stats = self.world.get_component(ai.current_target_id, ItemStats)
            yukkuri_stats = self.world.get_component(self.entity_id, YukkuriStats)

            # Retrieve action definition from Utility AI via blackboard or some other way
            # For now, we can just apply generic item effects if available
            if item_stats and yukkuri_stats:
                yukkuri_stats.hunger = max(0, yukkuri_stats.hunger - item_stats.nutrition)
                yukkuri_stats.happiness = min(100, yukkuri_stats.happiness + item_stats.fun)

                # Simple consume logic
                if item_stats.nutrition > 0:
                     # Destroy the entity properly in the world
                     # For tests, world._entities is used to check existence, but destroy_entity should remove it.
                     # Assuming destroy_entity handles it correctly.
                     self.world.destroy_entity(ai.current_target_id)
                     ai.current_target_id = -1

            return Status.SUCCESS

        return Status.RUNNING

class Idle(Action):
    def __init__(self, name="Idle", entity_id=None, world=None, blackboard=None):
        super().__init__(name, entity_id, world, blackboard)

    def update(self):
        phys = self.world.get_component(self.entity_id, PhysicsBody)
        if phys:
            phys.body.velocity = (0, 0)
        return Status.SUCCESS

# --- Behavior Tree Builder ---

def create_yukkuri_behavior_tree(entity_id, world, width, height):
    """
    Builds the behavior tree for a Yukkuri.

    Root
    |-- Selector
        |-- Sequence (Eat)
        |   |-- Check Goal == "Eat"
        |   |-- Selector (Find or Move)
        |       |-- Sequence (Target Exists?)
        |       |   |-- Check Target Valid
        |       |   |-- Selector (Close Enough?)
        |       |       |-- Sequence (Interact)
        |       |       |   |-- MoveToTarget (Close range) -> Actually MoveToTarget handles moving.
        |       |       |   |   If MoveToTarget succeeds (arrived), then Interact.
        |       |       |   |-- Interact
        |       |-- Find Food (Leaf that searches and sets target)
        |-- Sequence (Wander)
        |   |-- Check Goal == "Wander"
        |   |-- Wander
        |-- Idle
    """

    # Check Goal Condition
    def check_goal(goal_name):
        ai = world.get_component(entity_id, AIState)
        return ai and ai.current_action == goal_name

    # Check Target Condition
    def check_target_exists():
        ai = world.get_component(entity_id, AIState)
        if not ai or ai.current_target_id == -1:
            return False
        return world.has_component(ai.current_target_id, Transform)

    # Leaves
    move_to = MoveToTarget(entity_id=entity_id, world=world)
    interact = Interact(entity_id=entity_id, world=world)
    wander = Wander(entity_id=entity_id, world=world, width=width, height=height)
    idle = Idle(entity_id=entity_id, world=world)

    # --- Eat Branch ---
    eat_sequence = py_trees.composites.Sequence(name="Eat Sequence", memory=True)

    # 1. Check if we should be eating
    # Use a generic Check behavior if py_trees version differences (older versions had Check, newer use Decorators or specific classes)
    # Actually Check exists in 2.2.3 but structure might be different.
    # Let's check `py_trees` version. The installed is 2.4.0.
    # In 2.x, `py_trees.behaviours.Check` is indeed present. Wait, let me check docs/source if I can.
    # It seems `Check` was removed or I am misremembering.
    # Usually one uses a custom behaviour or a decorator.
    # Let's use a Functional Behaviour for simple checks.

    # Update: Check is NOT in standard behaviours list in recent versions.
    # We can implement a simple functional behaviour.

    class Check(Action):
        def __init__(self, name, check_fn):
             super().__init__(name)
             self.check_fn = check_fn

        def update(self):
            if self.check_fn():
                return Status.SUCCESS
            return Status.FAILURE

    is_eating = Check(name="Goal=Eat?", check_fn=lambda: check_goal("Eat"))

    # 2. Execution
    eat_execution = py_trees.composites.Selector(name="Eat Execution", memory=True)

    # 2a. If we have a target, Go to it and Eat
    have_target_seq = py_trees.composites.Sequence(name="Have Target?", memory=True)
    check_target = Check(name="Target Exists?", check_fn=check_target_exists)

    # Create specific instances for this sequence
    move_to_food = MoveToTarget(name="Move To Food", entity_id=entity_id, world=world)
    interact_food = Interact(name="Interact Food", entity_id=entity_id, world=world)

    have_target_seq.add_children([check_target, move_to_food, interact_food])

    # 2b. If no target, Find Food (This needs to be an action that sets target)
    # We'll implement a simple FindTarget action here or inline class
    class FindFood(Action):
        def update(self):
            super().update()
            ai = self.world.get_component(self.entity_id, AIState)
            trans = self.world.get_component(self.entity_id, Transform)

            # Reuse logic from System or reimplement
            # For brevity, simple search
            best_dist = float('inf')
            best_item = -1
            items = self.world.get_entities_with(ItemStats, Transform)

            for item in items:
                istats = self.world.get_component(item, ItemStats)
                itrans = self.world.get_component(item, Transform)
                if istats.nutrition > 0:
                    d = math.hypot(itrans.x - trans.x, itrans.y - trans.y)
                    if d < best_dist:
                        best_dist = d
                        best_item = item

            if best_item != -1:
                ai.current_target_id = best_item
                ai.path = None
                return Status.SUCCESS
            return Status.FAILURE

    find_food = FindFood(name="Find Food", entity_id=entity_id, world=world)

    eat_execution.add_children([have_target_seq, find_food])
    eat_sequence.add_children([is_eating, eat_execution])

    # --- Wander Branch ---
    wander_sequence = py_trees.composites.Sequence(name="Wander Sequence", memory=True)
    is_wandering = Check(name="Goal=Wander?", check_fn=lambda: check_goal("Wander") or check_goal("move_random")) # Handle legacy naming

    # We should check if we are already moving to a target from Wander action
    # Wander Action inside creates a target and moves.
    wander_sequence.add_children([is_wandering, wander])

    # --- Root ---
    root = py_trees.composites.Selector(name="Root", memory=False)
    root.add_children([eat_sequence, wander_sequence, idle])

    return root
