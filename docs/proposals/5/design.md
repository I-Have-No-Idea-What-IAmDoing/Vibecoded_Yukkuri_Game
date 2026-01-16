# Proposal 5: Audio System Optimizations

## 1. Introduction
The current `AudioManager` loads all sound effects directly into memory (`pygame.mixer.Sound`) and stores them in a dictionary. As the asset library grows (voice lines, varied SFX), this will lead to unbounded memory growth. Additionally, there is no enforcement of streaming for longer audio tracks, which can consume significant RAM if fully decoded.

## 2. Problem
- **Unbounded Memory Usage**: Every loaded sound stays in RAM until `clear()` is called.
- **Inefficient Large File Handling**: Music or long ambience tracks might be loaded as `Sound` objects instead of streamed, decompressing fully into raw PCM data in RAM.

## 3. Proposed Solution

### 3.1 LRU Cache for Sound Effects
Implement a Least Replacement Used (LRU) cache for the `sounds` dictionary, similar to the `SurfaceCache`.
- **Limit**: Configurable limit (e.g., 64MB of audio data or 200 distinct files).
- **Eviction**: When limit is reached, unload the least recently played sound.

### 3.2 Streaming Enforcement
Ensure that `play_music` or background ambience uses `pygame.mixer.music` which streams from disk, rather than pre-loading.
- **Threshold**: Any audio file > 10 seconds or > 500KB should be candidates for streaming if possible, though Pygame's mixer channel system is better for short SFX.
- **Music Manager**: dedicate `pygame.mixer.music` strictly for BGM.

### 3.3 Resource Management Integration
Update `ResourceManager` to defer sound loading or proxy it through the audio manager's cache policy.

## 4. Risks and Config
- **Latency**: Loading sound on demand (cache miss) introduces disk I/O latency.
- **Mitigation**: Pre-load common UI sounds (click, hover) and "keep" them protected from eviction.
