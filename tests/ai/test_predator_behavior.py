


import pytest
from unittest.mock import MagicMock
from yukkuri_game.engine.ecs import World
from yukkuri_game.game.yukkuri_components import Predator, AIState, YukkuriStats, Needs
from yukkuri_game.game.components import Transform, MovementController
from yukkuri_game.game.ai.behavior import FindPrey, EatPrey, Swoop
from yukkuri_game.game.yukkuri_components import Flight, FlightState
from py_trees.common import Status


@pytest.fixture
def world():
    return World()


@pytest.fixture
def predator_entity(world):
    entity = world.create_entity()
    world.add_component(entity, Predator(prey_sense_radius=100.0, dps=100.0, prey_tags={"Yukkuri", "reimu"}))
    world.add_component(entity, AIState())
    world.add_component(entity, Transform(x=0, y=0))
    world.add_component(entity, MovementController())
    return entity


@pytest.fixture
def prey_entity(world):
    entity = world.create_entity()
    world.add_component(entity, YukkuriStats(name="Prey", type_id="reimu"))
    world.add_component(entity, Needs(health=100.0, max_health=100.0))
    world.add_component(entity, Transform(x=30, y=0))
    # MovementController needed for EatPrey locking
    world.add_component(entity, MovementController())
    return entity


def test_find_prey(world, predator_entity, prey_entity):
    action = FindPrey(entity_id=predator_entity, world=world)

    status = action.update()

    assert status == Status.SUCCESS

    ai = world.get_component(predator_entity, AIState)
    assert ai.current_target_id == prey_entity


def test_find_prey_respects_range(world, predator_entity, prey_entity):
    # Move prey out of range
    prey_trans = world.get_component(prey_entity, Transform)
    prey_trans.x = 200.0  # > 100 radius

    action = FindPrey(entity_id=predator_entity, world=world)
    status = action.update()

    assert status == Status.FAILURE


def test_eat_prey_damage(world, predator_entity, prey_entity):
    ai = world.get_component(predator_entity, AIState)
    ai.current_target_id = prey_entity

    action = EatPrey(entity_id=predator_entity, world=world)

    # Needs locking support? Action checks controller/target_controller
    # Run once
    status = action.update()

    assert status == Status.RUNNING

    prey_needs = world.get_component(prey_entity, Needs)
    # Damage = dps (100) * dt (0.016) = 1.6
    assert prey_needs.health < 100.0
    assert 98.0 < prey_needs.health < 99.0


def test_eat_prey_consume(world, predator_entity, prey_entity):
    ai = world.get_component(predator_entity, AIState)
    ai.current_target_id = prey_entity

    prey_needs = world.get_component(prey_entity, Needs)
    prey_needs.health = 1.0  # 1 HP

    action = EatPrey(entity_id=predator_entity, world=world)

    status = action.update()

    # 1.0 - 1.6 <= 0 -> Consumed
    assert status == Status.SUCCESS

    # Verify prey destroyed
    assert not world.has_component(prey_entity, Needs)  # Entity likely deleted


def test_swoop_logic(world, predator_entity):
    world.add_component(
        predator_entity, Flight(state=FlightState.FLYING, altitude=60.0)
    )

    action = Swoop(entity_id=predator_entity, world=world)

    # 1. Start Swooping
    status = action.update()
    assert status == Status.RUNNING
    flight = world.get_component(predator_entity, Flight)
    assert flight.state == FlightState.SWOOPING

    # 2. Continue Swooping
    flight.altitude = 10.0
    status = action.update()
    assert status == Status.RUNNING

    # 3. Finish Swoop (near ground)
    flight.altitude = 4.0
    status = action.update()
    assert status == Status.SUCCESS
    assert flight.state == FlightState.GROUNDED
