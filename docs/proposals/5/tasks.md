# Tasks: Audio System Optimizations

- [ ] Refactor `AudioManager` to use `OrderedDict` for `sounds` <!-- id: 500 -->
- [ ] Implement `max_cache_size` logic (byte-size based preferred, or count based) <!-- id: 501 -->
- [ ] Add `play_music` method that enforces `pygame.mixer.music.load` and `play` <!-- id: 502 -->
- [ ] Create `PreloadedSounds` list for critical UI/Game events that never expire <!-- id: 503 -->
- [ ] Update `ResourceManager` to delegate sound loading to `AudioManager` (or respect its limits) <!-- id: 504 -->
- [ ] Test with memory profiler to verify cache eviction works <!-- id: 505 -->
