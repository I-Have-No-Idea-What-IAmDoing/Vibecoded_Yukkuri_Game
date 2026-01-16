import sys
import os
import psutil
import gc

# Make sure we can find the package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from loguru import logger
from yukkuri_game.engine.audio import AudioManager


def run_audio_benchmark(cycles=100, cache_limit=50):
    logger.info("Starting Audio Memory Benchmark...")

    # 1. Setup
    process = psutil.Process()
    initial_mem = process.memory_info().rss / 1024 / 1024
    logger.info(f"Initial Memory: {initial_mem:.2f} MB")

    # Initialize Audio Manager
    # Note: This might fail if no audio device, but headless environments often have dummy drivers.
    try:
        os.environ["SDL_AUDIODRIVER"] = "dummy"
        audio = AudioManager(sound_cache_limit=cache_limit)
    except Exception as e:
        logger.error(f"Failed to init audio: {e}")
        return

    if not audio.enabled:
        logger.warning("Audio disabled, cannot benchmark.")
        return

    # 2. Create Dummy Sound Files
    if not os.path.exists("benchmarks/temp_audio"):
        os.makedirs("benchmarks/temp_audio")

    # Generate a small wav file we can copy
    # We'll just define a path to a dummy file and hope we can write distinct files.
    # Actually, we can just load the SAME file with DIFFERENT names to trick the cache logic?
    # No, load_sound uses filepath as key for existence check? No, it uses 'name'.
    # But it calls pygame.mixer.Sound(filepath). If we use same filepath, pygame might cache internally?
    # Safest is to copy it.

    import wave
    import random

    logger.info(f"Generating {cycles} dummy sound files...")
    dummy_files = []

    # Generate a base 1-second silence/noise wav
    def generate_wav(filename):
        with wave.open(filename, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(44100)
            # 1 second of random noise (just to consume memory)
            data = bytearray(random.getrandbits(8) for _ in range(44100 * 2))
            wf.writeframes(data)

    for i in range(cycles):
        path = f"benchmarks/temp_audio/sound_{i}.wav"
        if not os.path.exists(path):
            try:
                generate_wav(path)
            except Exception as e:
                logger.error(f"Failed to generate sound: {e}")
                return
        dummy_files.append(path)

    # 3. Load Loop
    logger.info("loading sounds...")
    start_mem = process.memory_info().rss / 1024 / 1024

    for i, path in enumerate(dummy_files):
        name = f"sound_{i}"
        audio.load_sound(name, path)

        if i % 10 == 0:
            current_mem = process.memory_info().rss / 1024 / 1024
            count = len(audio.sounds)
            logger.debug(
                f"Loaded {i}/{cycles}. Cache Size: {count}. Mem: {current_mem:.2f} MB"
            )

    # 4. Final Check
    gc.collect()
    final_mem = process.memory_info().rss / 1024 / 1024
    cache_size = len(audio.sounds)

    logger.info(f"Final Memory: {final_mem:.2f} MB")
    logger.info(f"Final Cache Size: {cache_size}")
    logger.info(f"Total Change: {final_mem - start_mem:.2f} MB")

    if cache_size <= cache_limit:
        logger.info("PASS: Cache limit respected.")
    else:
        logger.error(f"FAIL: Cache limit exceeded ({cache_size} > {cache_limit})")

    # Cleanup
    for path in dummy_files:
        if os.path.exists(path):
            os.remove(path)
    os.rmdir("benchmarks/temp_audio")


if __name__ == "__main__":
    run_audio_benchmark()
