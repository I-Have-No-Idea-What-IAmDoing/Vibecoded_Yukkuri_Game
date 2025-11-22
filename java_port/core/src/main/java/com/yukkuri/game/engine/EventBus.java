package com.yukkuri.game.engine;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.function.Consumer;

public class EventBus {
    private final Map<Class<?>, List<Consumer<?>>> subscribers = new HashMap<>();

    public <E> void subscribe(Class<E> eventType, Consumer<E> handler) {
        subscribers.computeIfAbsent(eventType, k -> new ArrayList<>()).add(handler);
    }

    public <E> void unsubscribe(Class<E> eventType, Consumer<E> handler) {
        List<Consumer<?>> handlers = subscribers.get(eventType);
        if (handlers != null) {
            handlers.remove(handler);
        }
    }

    @SuppressWarnings("unchecked")
    public <E> void publish(E event) {
        List<Consumer<?>> handlers = subscribers.get(event.getClass());
        if (handlers != null) {
            // Iterate over a copy to avoid ConcurrentModificationException if a handler unsubscribes
            for (Consumer<?> handler : new ArrayList<>(handlers)) {
                ((Consumer<E>) handler).accept(event);
            }
        }
    }
}
