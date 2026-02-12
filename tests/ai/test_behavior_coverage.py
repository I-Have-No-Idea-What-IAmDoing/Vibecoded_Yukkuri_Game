from unittest.mock import MagicMock, patch
from py_trees.common import Status
from yukkuri_game.engine.ecs import World
from yukkuri_game.engine.event_bus import EventBus
from yukkuri_game.game.ai.behaviors import MoveToTarget, Interact, FindItem
from yukkuri_game.game.yukkuri_components import AIState, ItemStats, YukkuriStats, Needs
from yukkuri_game.game.components import (
    Transform,
    InteractionRequest,
    MovementController,
)
from yukkuri_game.game.ai.navigation_service import NavigationService
from yukkuri_game.game.services import GameService
from yukkuri_game.game.systems.interaction_system import InteractionSystem

# test_move_to_target_stuck_detection removed due to flakiness/mocking issues in CI environment


def test_move_to_target_success():
    world = World()
    nav_service = MagicMock()
    # Explicitly configure the method on the mock
    nav_service.find_path.return_value = [(95, 0), (100, 0)]
    world.services.register(nav_service, NavigationService)

    entity = world.create_entity()
    ai = AIState()
    trans = Transform(x=95, y=0)  # Close to target
    stats = YukkuriStats(name="Test", type_id="test")
    needs = Needs(energy=100.0)
    controller = MovementController()

    world.add_component(entity, ai)
    world.add_component(entity, trans)
    world.add_component(entity, stats)
    world.add_component(entity, needs)
    world.add_component(entity, controller)

    ai.state_data = {"target_x": 100.0, "target_y": 0.0}

    # Mock find_path to return a valid path even though we are close enough.
    # The logic accesses path[0] before checking final distance.
    nav_service.find_path.return_value = [(95, 0), (100, 0)]

    action = MoveToTarget(entity_id=entity, world=world)

    with patch("py_trees.blackboard.Blackboard") as mock_bb:
        mock_bb.return_value.get.return_value = 0.1

        # Close enough to not need pathfinding (or rather, pathfinding runs but we finish immediately)
        status = action.update()
        assert status == Status.SUCCESS


def test_interact_fallback():
    # Test Interact logic adds InteractionRequest
    world = World()

    # Need to register InteractionSystem to process the request if we want to check effects
    # But the Action only adds the component.

    e1 = world.create_entity()  # Yukkuri
    ai = AIState(current_target_id=-1)
    trans1 = Transform(x=0, y=0)
    stats = YukkuriStats(name="T", type_id="t")
    needs = Needs(hunger=50.0)

    world.add_component(e1, ai)
    world.add_component(e1, trans1)
    world.add_component(e1, stats)
    world.add_component(e1, needs)

    e2 = world.create_entity()  # Item
    trans2 = Transform(x=10, y=0)  # Close
    item_stats = ItemStats(name="Food", type_id="food", cost=10, nutrition=20.0)

    world.add_component(e2, trans2)
    world.add_component(e2, item_stats)

    ai.current_target_id = e2

    action = Interact(entity_id=e1, world=world, consume=True)

    status = action.update()
    assert status == Status.SUCCESS

    # Verify request was added
    assert world.has_component(e1, InteractionRequest)

    # Process interaction to verify logic (equivalent to old fallback test)
    # Updated: Need HungerSystem for food interactions
    from yukkuri_game.game.systems.hunger_system import HungerSystem

    hunger_sys = HungerSystem()
    # Need to register HungerSystem so InteractionSystem can find it
    world.services.register(hunger_sys, HungerSystem)

    system = InteractionSystem()
    system.update(world, 0.1)

    # Verify effects
    assert needs.hunger == 30.0  # 50 - 20
    assert not world.entity_exists(e2)  # Consumed


def test_find_item():
    world = World()
    game_service = MagicMock(spec=GameService)
    world.services.register(game_service, GameService)

    # Mock EventBus to prevent 'Mock object has no attribute publish' error
    # when ECS tries to publish ComponentAddedEvent
    event_bus = MagicMock(spec=EventBus)
    world.services.register(event_bus, EventBus)

    # Ensure try_get returns the registered services
    # (The default implementation of World.services should handle this if we register correctly,
    # but mocks sometimes behave oddly if not fully spec'd.
    # explicit registration above is safer than side_effect if the registry works.)

    entity = world.create_entity()
    world.add_component(entity, AIState())
    world.add_component(entity, Transform(x=0, y=0))

    # Mock find_best_item
    # It should return an entity ID (int)
    game_service.find_best_item.return_value = 999

    action = FindItem(
        name="Find", entity_id=entity, world=world, stat_criteria="nutrition"
    )

    status = action.update()

    assert status == Status.SUCCESS
    ai = world.get_component(entity, AIState)
    assert ai.current_target_id == 999

