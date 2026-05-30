"""
Module containing the ECS Entity Inspector & Query Tool UI.
"""

import ast
import dataclasses
from typing import Any
from typing import cast

import pygame
import pygame_gui
from pygame_gui.core import ObjectID
from pygame_gui.elements import UIButton
from pygame_gui.elements import UILabel
from pygame_gui.elements import UIPanel
from pygame_gui.elements import UITextEntryLine

from ...engine.components import PhysicsBody
from ...engine.components import Transform
from ...engine.ecs import World
from ...engine.event_bus import EventBus
from ...engine.systems.physics import PhysicsSystem
from ..events import EntitySelectedEvent
from .custom_elements import SafeUIScrollingContainer


class ECSInspector:
    """
    Searchable registry and live query/editing tool for ECS Entities.
    """

    def __init__(
        self,
        manager: pygame_gui.UIManager,
        container: UIPanel,
        world: World,
    ) -> None:
        """
        Initializes the ECSInspector.

        Args:
            manager (pygame_gui.UIManager): The UI Manager.
            container (UIPanel): The parent panel/container.
            world (World): The ECS World.
        """
        self.manager: pygame_gui.UIManager = manager
        self.container: UIPanel = container
        self.world: World = world

        self.selected_entity_id: int | None = None
        self.search_query: str = ""
        self.cached_entities_set: set[int] = set()

        self.live_track: bool = False
        self.collapsed_components: dict[str, bool] = {}
        self.component_headers: dict[UIButton, str] = {}
        self.filter_buttons: dict[UIButton, str] = {}
        self.read_only_labels: dict[UILabel, tuple[Any, str]] = {}

        # Mappings of UI elements to their editor metadata
        # Maps Element ->
        #   (entity_id, component_instance, field_name, field_type)
        self.field_editors: dict[Any, tuple[int, Any, str, type]] = {}
        # Maps Element -> entity_id (for the left registry list buttons)
        self.entity_buttons: dict[UIButton, int] = {}

        # Action Buttons
        self.focus_btn: UIButton | None = None
        self.select_btn: UIButton | None = None
        self.destroy_btn: UIButton | None = None
        self.live_track_btn: UIButton | None = None
        self.status_label: UILabel | None = None

        # Build initial UI structure
        self._setup_ui()

    def _setup_ui(self) -> None:
        """
        Builds the split-column layout inside the container.
        """
        width = self.container.rect.width
        height = self.container.rect.height

        # --- LEFT COLUMN (Entity Registry List) ---
        left_width = 210
        self.search_box = UITextEntryLine(
            relative_rect=pygame.Rect(5, 5, left_width, 30),
            manager=self.manager,
            container=self.container,
            placeholder_text="Filter components...",
        )

        # Quick Filter Pills
        pill_w = (left_width - 15) // 4
        pills_data = [
            ("All", ""),
            ("Yukkuri", "stats"),
            ("Phys", "physics"),
            ("Item", "item"),
        ]
        self.filter_buttons.clear()
        for idx, (label, query) in enumerate(pills_data):
            tip = (
                f"Filter entities by '{query}'"
                if query
                else "Clear all filters"
            )
            pill_btn = UIButton(
                relative_rect=pygame.Rect(
                    5 + idx * (pill_w + 5), 40, pill_w, 24
                ),
                text=label,
                manager=self.manager,
                container=self.container,
                object_id=ObjectID(class_id="quick_filter_pill"),
                tool_tip_text=tip,
            )
            self.filter_buttons[pill_btn] = query

        self.list_scroll = SafeUIScrollingContainer(
            relative_rect=pygame.Rect(5, 70, left_width, height - 80),
            manager=self.manager,
            container=self.container,
        )

        # --- RIGHT COLUMN (Selection details) ---
        right_x = left_width + 15
        right_width = width - right_x - 5

        # Inspect Label
        self.title_label = UILabel(
            relative_rect=pygame.Rect(right_x, 5, right_width - 110, 20),
            text="No Entity Inspected",
            manager=self.manager,
            container=self.container,
        )

        # Live Track Button
        self.live_track_btn = UIButton(
            relative_rect=pygame.Rect(width - 105, 5, 100, 20),
            text="Live: OFF",
            manager=self.manager,
            container=self.container,
            tool_tip_text="Toggle live real-time values tracking",
            object_id=ObjectID(class_id="live_track_btn"),
        )

        # Action buttons
        btn_w = (right_width - 10) // 3
        self.focus_btn = UIButton(
            relative_rect=pygame.Rect(right_x, 30, btn_w, 25),
            text="Focus Cam",
            manager=self.manager,
            container=self.container,
            tool_tip_text="Focus the game camera on this entity",
            object_id=ObjectID(class_id="focus_button"),
        )
        self.select_btn = UIButton(
            relative_rect=pygame.Rect(right_x + btn_w + 5, 30, btn_w, 25),
            text="Select Game",
            manager=self.manager,
            container=self.container,
            tool_tip_text="Select this entity in the gameplay HUD",
            object_id=ObjectID(class_id="select_button"),
        )
        self.destroy_btn = UIButton(
            relative_rect=pygame.Rect(right_x + 2 * btn_w + 10, 30, btn_w, 25),
            text="Destroy",
            manager=self.manager,
            container=self.container,
            tool_tip_text="Destroy this entity cleanly",
            object_id=ObjectID(class_id="destroy_button"),
        )

        self.focus_btn.disable()
        self.select_btn.disable()
        self.destroy_btn.disable()

        # Component Field Editor Scroll Container
        self.editor_scroll = SafeUIScrollingContainer(
            relative_rect=pygame.Rect(
                right_x, 60, right_width, height - 105
            ),
            manager=self.manager,
            container=self.container,
        )

        # Editor Status Label
        self.status_label = UILabel(
            relative_rect=pygame.Rect(
                right_x, height - 35, right_width, 25
            ),
            text="",
            manager=self.manager,
            container=self.container,
            object_id=ObjectID(class_id="editor_status"),
        )

        self._refresh_entity_list()

    def _refresh_entity_list(self) -> None:
        """
        Queries and filters active entities, and repopulates the left column.
        """
        # Clear previous entity list buttons
        for btn in list(self.entity_buttons.keys()):
            btn.kill()  # type: ignore[no-untyped-call]
        self.entity_buttons.clear()

        # Gather matching entities
        matching_entities: list[int] = []
        all_entities = self.world.get_all_entities()
        self.cached_entities_set = set(all_entities)

        # Parse query components
        query_parts = [
            q.strip().lower()
            for q in self.search_query.split(",")
            if q.strip()
        ]

        for entity in all_entities:
            comps = self.world.get_all_components(entity)
            comp_names = [type(c).__name__.lower() for c in comps]

            # Match all query terms (e.g. partial matches)
            matches = True
            for part in query_parts:
                term_matched = False
                for name in comp_names:
                    if part in name:
                        term_matched = True
                        break
                if not term_matched:
                    matches = False
                    break

            if matches:
                matching_entities.append(entity)

        # Populate the scroll container
        y_pos = 2
        btn_h = 24
        spacing = 4

        for entity in matching_entities:
            comps = self.world.get_all_components(entity)
            main_comp = ""
            for c in comps:
                name = type(c).__name__
                if "Stats" in name or "Body" in name or "Transform" in name:
                    main_comp = f" [{name}]"
                    break

            btn_text = f"Entity {entity}{main_comp}"
            btn = UIButton(
                relative_rect=pygame.Rect(2, y_pos, 180, btn_h),
                text=btn_text,
                manager=self.manager,
                container=self.list_scroll,
                object_id=ObjectID(class_id="entity_list_button"),
            )

            # Highlight selected
            if entity == self.selected_entity_id:
                btn.select()  # type: ignore[no-untyped-call]

            self.entity_buttons[btn] = entity
            y_pos += btn_h + spacing

        self.list_scroll.set_scrollable_area_dimensions(
            (184, max(y_pos, self.list_scroll.rect.height))
        )

    def _refresh_editor_panel(self) -> None:
        """
        Clears and repopulates component field editors for the selected
        entity.
        """
        # Clear existing editors
        for widget in list(self.field_editors.keys()):
            widget.kill()  # type: ignore[no-untyped-call]
        self.field_editors.clear()
        self.component_headers.clear()
        self.read_only_labels.clear()

        # Clear container completely to avoid residual labels
        self.editor_scroll.kill()  # type: ignore[no-untyped-call]

        width = self.container.rect.width
        left_width = 210
        right_x = left_width + 15
        right_width = width - right_x - 5
        height = self.container.rect.height

        self.editor_scroll = SafeUIScrollingContainer(
            relative_rect=pygame.Rect(
                right_x, 60, right_width, height - 105
            ),
            manager=self.manager,
            container=self.container,
        )

        if self.selected_entity_id is None or not self.world.entity_exists(
            self.selected_entity_id
        ):
            self.title_label.set_text("No Entity Inspected")
            if self.focus_btn:
                self.focus_btn.disable()
            if self.select_btn:
                self.select_btn.disable()
            if self.destroy_btn:
                self.destroy_btn.disable()
            return

        entity = self.selected_entity_id
        self.title_label.set_text(f"Inspecting Entity {entity}")
        if self.focus_btn:
            self.focus_btn.enable()
        if self.select_btn:
            self.select_btn.enable()
        if self.destroy_btn:
            self.destroy_btn.enable()

        components = self.world.get_all_components(entity)

        y_pos = 5
        scroll_w = right_width - 25

        for comp in components:
            comp_name = type(comp).__name__
            comp_collapsed = self.collapsed_components.get(comp_name, False)
            arrow = ">" if comp_collapsed else "v"

            # List fields
            fields_list: list[tuple[str, Any, Any]] = []
            if dataclasses.is_dataclass(comp):
                for f in dataclasses.fields(comp):
                    fields_list.append(
                        (f.name, getattr(comp, f.name), f.type)
                    )
            else:
                for attr_name in dir(comp):
                    if attr_name.startswith("_"):
                        continue
                    attr_val = getattr(comp, attr_name)
                    if callable(attr_val):
                        continue
                    fields_list.append((attr_name, attr_val, type(attr_val)))

            # Component Header Toggle Button
            header_btn = UIButton(
                relative_rect=pygame.Rect(2, y_pos, scroll_w, 24),
                text=f" {arrow} {comp_name} ({len(fields_list)} fields)",
                manager=self.manager,
                container=self.editor_scroll,
                object_id=ObjectID(class_id="comp_header_btn"),
            )
            self.component_headers[header_btn] = comp_name
            y_pos += 26

            if comp_collapsed:
                y_pos += 4  # Spacing
                continue

            # Draw editors for fields
            for name, val, f_type in fields_list:
                # Label on left, input on right
                label_w = int(scroll_w * 0.45)
                input_w = scroll_w - label_w - 5

                if isinstance(f_type, str):
                    # Annotations can be strings due to PEP 563
                    # Fall back to checking runtime type
                    f_type = type(val)

                type_name = (
                    f_type.__name__
                    if hasattr(f_type, "__name__")
                    else str(f_type)
                )
                label_text = f"  {name} [{type_name}]:"

                UILabel(
                    relative_rect=pygame.Rect(5, y_pos, label_w, 20),
                    text=label_text,
                    manager=self.manager,
                    container=self.editor_scroll,
                )

                # Boolean Toggle Button
                if f_type is bool or isinstance(val, bool):
                    btn = UIButton(
                        relative_rect=pygame.Rect(
                            label_w + 5, y_pos, input_w, 20
                        ),
                        text=str(val),
                        manager=self.manager,
                        container=self.editor_scroll,
                    )
                    self.field_editors[btn] = (entity, comp, name, bool)

                # Editable Text Entry for numbers / strings
                elif f_type in (int, float, str) or isinstance(
                    val, (int, float, str)
                ):
                    entry = UITextEntryLine(
                        relative_rect=pygame.Rect(
                            label_w + 5, y_pos - 2, input_w, 24
                        ),
                        manager=self.manager,
                        container=self.editor_scroll,
                    )
                    entry.set_text(str(val))
                    actual_type = (
                        f_type
                        if f_type in (int, float, str)
                        else type(val)
                    )
                    self.field_editors[entry] = (
                        entity,
                        comp,
                        name,
                        actual_type,
                    )

                # Non-primitive fields shown as read-only labels
                else:
                    lbl = UILabel(
                        relative_rect=pygame.Rect(
                            label_w + 5, y_pos, input_w, 20
                        ),
                        text=str(val),
                        manager=self.manager,
                        container=self.editor_scroll,
                    )
                    self.read_only_labels[lbl] = (comp, name)

                y_pos += 24

            y_pos += 8  # Spacing between components

        self.editor_scroll.set_scrollable_area_dimensions(
            (scroll_w, max(y_pos, self.editor_scroll.rect.height))
        )

    def update(self, dt: float) -> None:
        """
        Updates the inspector panel state. Called once per frame.

        Args:
            dt (float): Delta time.
        """
        # Periodically verify if the selected entity was destroyed
        if (
            self.selected_entity_id is not None
            and not self.world.entity_exists(self.selected_entity_id)
        ):
            self.selected_entity_id = None
            self._refresh_editor_panel()

        # Update entity list if entities spawned or destroyed
        current_entities = set(self.world.get_all_entities())
        if current_entities != self.cached_entities_set:
            self._refresh_entity_list()

        # Update live values if tracking is enabled
        if (
            self.live_track
            and self.selected_entity_id is not None
            and self.world.entity_exists(self.selected_entity_id)
        ):
            self._update_live_values()

    def _update_live_values(self) -> None:
        """
        Updates UI elements with current component field values in real-time.
        """
        # 1. Update primitive field editors
        for widget, (entity_id, comp, field_name, f_type) in list(
            self.field_editors.items()
        ):
            # If the user is currently editing this field, skip it
            focus_set = self.manager.get_focus_set()
            if focus_set and widget in focus_set:
                continue

            try:
                current_val = getattr(comp, field_name)
                val_str = str(current_val)

                if isinstance(widget, UIButton):
                    if widget.text != val_str:
                        widget.set_text(val_str)
                elif isinstance(widget, UITextEntryLine):
                    if widget.get_text() != val_str:
                        widget.set_text(val_str)
            except Exception:
                pass

        # 2. Update read-only labels
        for label, (comp, field_name) in list(self.read_only_labels.items()):
            try:
                current_val = getattr(comp, field_name)
                val_str = str(current_val)
                if label.text != val_str:
                    label.set_text(val_str)
            except Exception:
                pass

    def process_event(self, event: pygame.event.Event) -> bool:
        """
        Handles Pygame events dispatched from the main HUD loop.

        Args:
            event (pygame.event.Event): The Pygame event.

        Returns:
            bool: True if the event was consumed, False otherwise.
        """
        # 1. Text Entry Finished (Live numeric/string value editing)
        if event.type == pygame_gui.UI_TEXT_ENTRY_FINISHED:
            if event.ui_element == self.search_box:
                self.search_query = event.text
                self._refresh_entity_list()
                return True

            elif event.ui_element in self.field_editors:
                entity, comp, field_name, f_type = self.field_editors[
                    event.ui_element
                ]
                new_text = event.text
                old_val = getattr(comp, field_name)

                try:
                    parsed_val = self._cast_value(new_text, f_type)
                    self._set_component_field(
                        entity, comp, field_name, parsed_val
                    )
                    if self.status_label:
                        self.status_label.set_text(
                            f"Updated '{field_name}' to {parsed_val}"
                        )
                except Exception:
                    # Parse failed: restore old value, show error feedback
                    event.ui_element.set_text(str(old_val))
                    err_msg = f"Error: Invalid '{f_type.__name__}' value"
                    if self.status_label:
                        self.status_label.set_text(err_msg)

                return True

        # 2. Button Clicks (Registry List, Actions, Booleans)
        elif event.type == pygame_gui.UI_BUTTON_PRESSED:
            # Clicked an entity on the registry list
            if event.ui_element in self.entity_buttons:
                # Unselect previous
                for btn in self.entity_buttons:
                    btn.unselect()  # type: ignore[no-untyped-call]

                entity_id = self.entity_buttons[event.ui_element]
                self.selected_entity_id = entity_id
                event.ui_element.select()  # type: ignore[no-untyped-call]

                if self.status_label:
                    self.status_label.set_text(
                        f"Inspecting entity {entity_id}."
                    )
                self._refresh_editor_panel()
                return True

            # Quick Filter pill button clicked
            elif event.ui_element in self.filter_buttons:
                for btn in self.filter_buttons:
                    if btn == event.ui_element:
                        btn.select()  # type: ignore[no-untyped-call]
                    else:
                        btn.unselect()  # type: ignore[no-untyped-call]

                query = self.filter_buttons[event.ui_element]
                self.search_query = query
                self.search_box.set_text(query)
                self._refresh_entity_list()
                return True

            # Live Track Toggle clicked
            elif event.ui_element == self.live_track_btn:
                self.live_track = not self.live_track
                btn = self.live_track_btn
                if btn:
                    if self.live_track:
                        btn.select()  # type: ignore[no-untyped-call]
                        btn.set_text("Live: ON")
                        if self.status_label:
                            self.status_label.set_text("Live tracking enabled.")
                    else:
                        btn.unselect()  # type: ignore[no-untyped-call]
                        btn.set_text("Live: OFF")
                        if self.status_label:
                            self.status_label.set_text(
                                "Live tracking disabled."
                            )
                return True

            # Collapsible component header button clicked
            elif event.ui_element in self.component_headers:
                comp_name = self.component_headers[event.ui_element]
                curr_collapsed = self.collapsed_components.get(
                    comp_name, False
                )
                self.collapsed_components[comp_name] = not curr_collapsed
                self._refresh_editor_panel()
                return True

            # Boolean Field Toggle clicked
            elif event.ui_element in self.field_editors:
                entity, comp, field_name, _ = self.field_editors[
                    event.ui_element
                ]
                current_val = bool(getattr(comp, field_name))
                new_val = not current_val

                self._set_component_field(entity, comp, field_name, new_val)
                event.ui_element.set_text(str(new_val))
                if self.status_label:
                    self.status_label.set_text(
                        f"Toggled '{field_name}' to {new_val}"
                    )
                return True

            # Action: Focus Camera
            elif event.ui_element == self.focus_btn:
                if (
                    self.selected_entity_id is not None
                    and self.world.entity_exists(self.selected_entity_id)
                ):
                    trans = self.world.try_get_component(
                        self.selected_entity_id, Transform
                    )

                    try:
                        # Grab camera from system or scene
                        app_cls = self.world.services.get(
                            cast(Any, "Application")
                        )
                        cam = app_cls.scene_manager.current_scene.camera
                        if cam and trans:
                            cam.tracked_entity_id = self.selected_entity_id
                            cam.camera_x = trans.x
                            cam.camera_y = trans.y
                            if self.status_label:
                                self.status_label.set_text("Camera focused.")
                    except Exception:
                        pass
                return True

            # Action: Select in Game (sync selection with HUD primary panel)
            elif event.ui_element == self.select_btn:
                if (
                    self.selected_entity_id is not None
                    and self.world.entity_exists(self.selected_entity_id)
                ):
                    event_bus = self.world.services.try_get(EventBus)
                    if event_bus:
                        # Trigger Primary Selection in HUD
                        event_bus.publish(
                            EntitySelectedEvent(
                                entity_ids=(self.selected_entity_id,)
                            )
                        )
                        if self.status_label:
                            self.status_label.set_text("Selected in game HUD.")
                return True

            # Action: Destroy Entity
            elif event.ui_element == self.destroy_btn:
                if (
                    self.selected_entity_id is not None
                    and self.world.entity_exists(self.selected_entity_id)
                ):
                    self.world.destroy_entity(self.selected_entity_id)
                    if self.status_label:
                        self.status_label.set_text(
                            f"Entity {self.selected_entity_id} destroyed."
                        )
                    self.selected_entity_id = None
                    self._refresh_editor_panel()
                return True

        return False

    def _cast_value(self, text: str, target_type: type) -> Any:
        """
        Parses and casts string input safely into target type representation.
        """
        if target_type is bool:
            return text.lower() in ("true", "1", "yes")
        elif target_type is int:
            return int(text)
        elif target_type is float:
            return float(text)
        elif target_type is str:
            return text
        else:
            # Fall back to evaluation of structures (tuples, lists, dicts)
            val = ast.literal_eval(text)
            if isinstance(val, target_type) or target_type is Any:
                return val
            raise TypeError(f"Cannot cast value to {target_type}")

    def _set_component_field(
        self, entity_id: int, component: Any, field_name: str, value: Any
    ) -> None:
        """
        Safely assigns values with Pymunk Physics synchronization.
        """
        setattr(component, field_name, value)

        # Sync Transform position to PhysicsBody immediately
        if isinstance(component, Transform) and field_name in ("x", "y"):
            phys = self.world.try_get_component(entity_id, PhysicsBody)
            if phys and phys.body:
                if field_name == "x":
                    phys.body.position = (value, phys.body.position.y)
                elif field_name == "y":
                    phys.body.position = (phys.body.position.x, value)

                # Reindex Pymunk shapes immediately so collision triggers update
                try:
                    phys_sys = self.world.get_system(PhysicsSystem)
                    phys_sys.space.reindex_shapes_for_body(phys.body)
                except Exception:
                    pass
