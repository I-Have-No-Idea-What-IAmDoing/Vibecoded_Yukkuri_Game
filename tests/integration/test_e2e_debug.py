from yukkuri_game.testing.driver import GameDriver
from yukkuri_game.game.components import YukkuriStats
from yukkuri_game.engine.services.time_service import TimeService

def test_debug_age(game_driver: GameDriver) -> None:
    driver = game_driver
    driver.setup()
    
    time_service = driver.world.services.get(TimeService)
    print("\nSCALE:", time_service.scale)
    print("GAME SPEED:", time_service.game_speed)
    print("MULTIPLIER:", time_service.game_delta_multiplier)
    
    reimu_id = driver.yukkuri_builder("reimu").at(100.0, 100.0).build()
    stats = driver.get_component(reimu_id, YukkuriStats)
    stats.growth_stage = "Baby"
    stats.age = 99.9
    print("BEFORE AGE:", stats.age, stats.growth_stage)
    driver.run_for(1.0)
    print("AFTER AGE:", stats.age, stats.growth_stage)
