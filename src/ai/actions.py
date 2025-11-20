import random
import math

class Actions:
    @staticmethod
    def execute_eat(yukkuri, yukkurrium, dt):
        # If no target, find closest food
        if not yukkuri.action_target or yukkuri.action_target not in yukkurrium.items:
            closest_food = None
            min_dist = float('inf')
            for item in yukkurrium.items:
                if item.type == 'food':
                    dist = math.hypot(yukkuri.position[0] - item.position[0], yukkuri.position[1] - item.position[1])
                    if dist < min_dist:
                        min_dist = dist
                        closest_food = item
            yukkuri.action_target = closest_food

        target = yukkuri.action_target
        if target:
            # Move towards
            dx = target.position[0] - yukkuri.position[0]
            dy = target.position[1] - yukkuri.position[1]
            dist = math.hypot(dx, dy)

            if dist < 5: # Close enough to eat
                nutrition = target.data.get('nutrition', 10)
                yukkuri.stats['hunger'] = min(yukkuri.max_stats['hunger'], yukkuri.stats['hunger'] + nutrition)
                yukkurrium.remove_item(target)
                yukkuri.action_target = None
                yukkuri.current_action = None # Done
                yukkuri.velocity = [0, 0]
            else:
                # Normalize and move
                speed = 50
                yukkuri.velocity = [dx/dist * speed, dy/dist * speed]
        else:
            # No food found, idle
            yukkuri.velocity = [0, 0]
            yukkuri.current_action = None

    @staticmethod
    def execute_sleep(yukkuri, yukkurrium, dt):
        yukkuri.velocity = [0, 0]
        yukkuri.stats['energy'] = min(yukkuri.max_stats['energy'], yukkuri.stats['energy'] + 10 * dt)
        if yukkuri.stats['energy'] >= 95:
            yukkuri.current_action = None # Wake up

    @staticmethod
    def execute_wander(yukkuri, yukkurrium, dt):
        # Initialize state if not present or if new wander session
        if not hasattr(yukkuri, 'wander_timer'):
            yukkuri.wander_timer = 0

        # Start moving if just started (or if velocity is 0 for some reason)
        if yukkuri.wander_timer == 0 and yukkuri.velocity == [0, 0]:
            angle = random.random() * 2 * math.pi
            speed = 30
            yukkuri.velocity = [math.cos(angle) * speed, math.sin(angle) * speed]

        # Update timer
        yukkuri.wander_timer += dt

        # Change direction occasionally
        if random.random() < 0.05:
            angle = random.random() * 2 * math.pi
            speed = 30
            yukkuri.velocity = [math.cos(angle) * speed, math.sin(angle) * speed]

        # Finish wandering after some time to re-evaluate needs
        if yukkuri.wander_timer > 2.0: # 2 seconds wander duration
            yukkuri.current_action = None
            yukkuri.velocity = [0, 0]
            yukkuri.wander_timer = 0

    @staticmethod
    def execute_play(yukkuri, yukkurrium, dt):
        # If no target, find closest toy
        if not yukkuri.action_target or yukkuri.action_target not in yukkurrium.items:
            closest_toy = None
            min_dist = float('inf')
            for item in yukkurrium.items:
                if item.type == 'toy':
                    dist = math.hypot(yukkuri.position[0] - item.position[0], yukkuri.position[1] - item.position[1])
                    if dist < min_dist:
                        min_dist = dist
                        closest_toy = item
            yukkuri.action_target = closest_toy

        target = yukkuri.action_target
        if target:
            # Move towards
            dx = target.position[0] - yukkuri.position[0]
            dy = target.position[1] - yukkuri.position[1]
            dist = math.hypot(dx, dy)

            if dist < 10: # Close enough to play
                fun = target.data.get('fun', 10)
                # Increase happiness
                yukkuri.stats['happiness'] = min(yukkuri.max_stats['happiness'], yukkuri.stats['happiness'] + fun * dt * 5)

                # Stop moving
                yukkuri.velocity = [0, 0]

                # Chance to stop playing if happy enough or random
                if yukkuri.stats['happiness'] >= 95 or random.random() < 0.01:
                     yukkuri.current_action = None
                     yukkuri.action_target = None
            else:
                # Normalize and move
                speed = 60
                yukkuri.velocity = [dx/dist * speed, dy/dist * speed]
        else:
            # No toy found, fallback to idle/wander
            yukkuri.current_action = None
            yukkuri.velocity = [0, 0]
