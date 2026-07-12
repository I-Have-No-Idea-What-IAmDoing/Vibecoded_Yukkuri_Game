import sys
import os
import pymunk

# Add src to path
sys.path.insert(0, os.path.abspath("src"))

from yukkuri_game.testing.driver import GameDriver
from yukkuri_game.engine.components import Transform, PhysicsBody
from yukkuri_game.game.components import GossipQueue
from yukkuri_game.game.systems.gossip_system import GossipSystem
from yukkuri_game.game.services.interfaces import IPhysicsService

driver = GameDriver()
driver.setup()

reimu_a = driver.yukkuri_builder("reimu").at(50.0, 100.0).build()
reimu_b = driver.yukkuri_builder("reimu").at(90.0, 100.0).build()
witness = driver.yukkuri_builder("reimu").at(250.0, 100.0).build()

wall_id = driver.item_builder("wall").at(150.0, 100.0).build()

space = driver.world.services.get(IPhysicsService).space
space.gravity = (0, 0)

pb = driver.get_component(wall_id, PhysicsBody)
print(f"Before static change: body position = {pb.body.position}, body type = {pb.body.body_type}")
space.remove(pb.body, pb.shape)
pb.body.body_type = pymunk.Body.STATIC
space.add(pb.body, pb.shape)
print(f"After static change: body position = {pb.body.position}, body type = {pb.body.body_type}")

driver.run_for(0.02)

pos_a = driver.get_component(reimu_a, Transform)
pos_w = driver.get_component(witness, Transform)
pos_wall = driver.get_component(wall_id, Transform)

print(f"reimu_a Transform: x={pos_a.x}, y={pos_a.y}")
print(f"witness Transform: x={pos_w.x}, y={pos_w.y}")
print(f"wall Transform: x={pos_wall.x}, y={pos_wall.y}")
print(f"wall Physics position: {pb.body.position}")

start_pos = (pos_a.x, pos_a.y)
end_pos = (pos_w.x, pos_w.y)
print(f"Querying from {start_pos} to {end_pos}")

queries = space.segment_query(start_pos, end_pos, 1.0, pymunk.ShapeFilter())
print(f"Number of query hits: {len(queries)}")
for q in queries:
    print(f"  Hit shape: {q.shape}, point: {q.point}, normal: {q.normal}, alpha: {q.alpha}")
    print(f"  Shape body position: {q.shape.body.position}, body type: {q.shape.body.body_type}")

gossip_system = driver.world.get_system(GossipSystem)
los = gossip_system._check_line_of_sight(driver.world, pos_a, pos_w, start_id=reimu_a, end_id=witness)
print(f"Line of sight check returned: {los}")
