use bevy::prelude::*;
use bevy::log::BoxedLayer;
use bevy::log::tracing_subscriber::Layer;
use bevy::log::tracing::{self, Subscriber, field::{Field, Visit}};
use std::collections::VecDeque;
use std::sync::{Mutex, OnceLock};

static LOG_BUFFER: OnceLock<Mutex<VecDeque<String>>> = OnceLock::new();

/// Returns a reference to the global thread-safe log buffer.
pub fn get_log_buffer() -> &'static Mutex<VecDeque<String>> {
    LOG_BUFFER.get_or_init(|| Mutex::new(VecDeque::new()))
}

/// A visitor that extracts the message field from a tracing event.
#[derive(Default)]
struct StringVisitor {
    message: String,
}

impl Visit for StringVisitor {
    fn record_debug(&mut self, field: &Field, value: &dyn std::fmt::Debug) {
        if field.name() == "message" {
            // Format without standard Debug quotes for string fields.
            let formatted = format!("{:?}", value);
            // Strip leading/trailing quotes if it's a string literal.
            if formatted.starts_with('"') && formatted.ends_with('"') && formatted.len() >= 2 {
                self.message = formatted[1..formatted.len() - 1].to_string();
            } else {
                self.message = formatted;
            }
        }
    }
}

/// A custom tracing Subscriber Layer that buffers logs in memory.
pub struct ConsoleLayer;

impl<S: Subscriber> Layer<S> for ConsoleLayer {
    fn on_event(
        &self,
        event: &tracing::Event<'_>,
        _ctx: bevy::log::tracing_subscriber::layer::Context<'_, S>,
    ) {
        let mut visitor = StringVisitor::default();
        event.record(&mut visitor);

        let metadata = event.metadata();
        let level = metadata.level();
        let target = metadata.target();

        // Format message as: [LEVEL] [TARGET] Message
        let formatted = format!("[{}] [{}] {}", level, target, visitor.message);

        if let Ok(mut buffer) = get_log_buffer().lock() {
            buffer.push_back(formatted);
            if buffer.len() > 1000 {
                buffer.pop_front();
            }
        }
    }
}

/// Helper function to provide Bevy's LogPlugin with our custom layer.
pub fn get_console_layer(_app: &mut App) -> Option<BoxedLayer> {
    Some(ConsoleLayer.boxed())
}

/// Resource holding the logs for Bevy UI rendering.
#[derive(Resource, Default, Debug, Clone)]
pub struct ConsoleLogBuffer {
    pub logs: Vec<String>,
    pub was_updated: bool,
}

/// System that copies logs from the thread-safe static buffer into Bevy resource space.
pub fn update_console_log_buffer_system(mut buffer: ResMut<ConsoleLogBuffer>) {
    buffer.was_updated = false;
    if let Ok(mut global_buf) = get_log_buffer().lock() {
        if !global_buf.is_empty() {
            for log_msg in global_buf.drain(..) {
                buffer.logs.push(log_msg);
            }
            if buffer.logs.len() > 1000 {
                let start_idx = buffer.logs.len() - 1000;
                buffer.logs.drain(0..start_idx);
            }
            buffer.was_updated = true;
        }
    }
}
