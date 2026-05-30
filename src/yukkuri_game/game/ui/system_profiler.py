"""
Module containing the ECS System Performance Profiler UI.
"""

import time

import pygame
import pygame_gui
from pygame_gui.core import ObjectID
from pygame_gui.elements import UIButton
from pygame_gui.elements import UILabel
from pygame_gui.elements import UIPanel
from .custom_elements import SafeUIScrollingContainer

from ...engine.ecs import World


class SystemProfiler:
    """
    Profiler panel measuring and visualizing real-time ECS system timings.
    """

    def __init__(
        self,
        manager: pygame_gui.UIManager,
        container: UIPanel,
        world: World,
    ) -> None:
        """
        Initializes the SystemProfiler.

        Args:
            manager (pygame_gui.UIManager): The UI Manager.
            container (UIPanel): The parent panel/container.
            world (World): The ECS World.
        """
        self.manager: pygame_gui.UIManager = manager
        self.container: UIPanel = container
        self.world: World = world

        self.fps_target: int = 60
        self.budget_ms: float = 16.67

        # System peaks and timestamps (for 5s rolling decay)
        self.system_peaks: dict[str, float] = {}
        self.peak_timestamps: dict[str, float] = {}

        # Mappings of elements to identify them
        self.row_labels: list[list[UILabel]] = []

        # High performance row cache
        self.row_systems: list[str] = [""] * 25
        self.row_hot_states: list[bool] = [False] * 25
        self.bar_fill_color: str = ""
        self.update_timer: float = 0.0

        # Setup layout
        self._setup_ui()

    def _setup_ui(self) -> None:
        """
        Builds the profiler tab interface.
        """
        width = self.container.rect.width
        height = self.container.rect.height

        # --- CONTROLS ROW ---
        y_pos = 5
        btn_w = 140
        spacing = 10

        self.profile_btn = UIButton(
            relative_rect=pygame.Rect(5, y_pos, btn_w, 25),
            text="Profile: OFF",
            manager=self.manager,
            container=self.container,
            tool_tip_text="Toggle ECS System profiling timings collection",
            object_id=ObjectID(class_id="profile_toggle"),
        )
        if self.world.debug_timing:
            self.profile_btn.select()  # type: ignore[no-untyped-call]
            self.profile_btn.set_text("Profile: ON")

        self.target_btn = UIButton(
            relative_rect=pygame.Rect(5 + btn_w + spacing, y_pos, btn_w, 25),
            text="Target: 60 FPS",
            manager=self.manager,
            container=self.container,
            tool_tip_text="Toggle frame budget target between 60 & 30 FPS",
            object_id=ObjectID(class_id="budget_target_btn"),
        )

        self.reset_peaks_btn = UIButton(
            relative_rect=pygame.Rect(
                5 + 2 * (btn_w + spacing), y_pos, btn_w, 25
            ),
            text="Reset Peaks",
            manager=self.manager,
            container=self.container,
            tool_tip_text="Manually clear and reset all system peak timings",
        )

        y_pos += 35

        # --- GRAPHICAL BUDGET PROGRESS BAR ---
        self.budget_label = UILabel(
            relative_rect=pygame.Rect(5, y_pos, width - 10, 20),
            text="Frame Budget Usage: 0.00ms / 16.67ms (0.0%)",
            manager=self.manager,
            container=self.container,
        )
        y_pos += 22

        # Progress bar container panel
        self.bar_bg = UIPanel(
            relative_rect=pygame.Rect(5, y_pos, width - 10, 20),
            manager=self.manager,
            container=self.container,
            object_id=ObjectID(class_id="budget_bg"),
        )
        self.bar_fill: UIPanel | None = None
        y_pos += 30

        # --- TABLE HEADER ---
        col_x = [5, 250, 350, 450]
        col_w = [240, 95, 95, 95]

        UILabel(
            relative_rect=pygame.Rect(col_x[0], y_pos, col_w[0], 20),
            text="System Name",
            manager=self.manager,
            container=self.container,
        )
        UILabel(
            relative_rect=pygame.Rect(col_x[1], y_pos, col_w[1], 20),
            text="Avg (ms)",
            manager=self.manager,
            container=self.container,
        )
        UILabel(
            relative_rect=pygame.Rect(col_x[2], y_pos, col_w[2], 20),
            text="Peak (ms)",
            manager=self.manager,
            container=self.container,
        )
        UILabel(
            relative_rect=pygame.Rect(col_x[3], y_pos, col_w[3], 20),
            text="% Budget",
            manager=self.manager,
            container=self.container,
        )
        y_pos += 22

        # --- TABLE SCROLL CONTAINER ---
        self.list_scroll = SafeUIScrollingContainer(
            relative_rect=pygame.Rect(
                5, y_pos, width - 10, height - y_pos - 10
            ),
            manager=self.manager,
            container=self.container,
        )

        self._refresh_system_list()

    def _refresh_system_list(self) -> None:
        """
        Clears and rebuilds the scrollable table row contents.
        """
        # Clear existing rows
        for row in self.row_labels:
            for lbl in row:
                lbl.kill()  # type: ignore[no-untyped-call]
        self.row_labels.clear()
        self.row_systems = [""] * 25
        self.row_hot_states = [False] * 25

        # Populate rows
        y_pos = 2
        row_h = 24
        spacing = 4

        col_x = [2, 242, 342, 442]
        col_w = [238, 96, 96, 96]
        scroll_w = self.container.rect.width - 35

        for _ in range(25):
            name_lbl = UILabel(
                relative_rect=pygame.Rect(col_x[0], y_pos, col_w[0], row_h),
                text="",
                manager=self.manager,
                container=self.list_scroll,
            )
            avg_lbl = UILabel(
                relative_rect=pygame.Rect(col_x[1], y_pos, col_w[1], row_h),
                text="",
                manager=self.manager,
                container=self.list_scroll,
            )
            peak_lbl = UILabel(
                relative_rect=pygame.Rect(col_x[2], y_pos, col_w[2], row_h),
                text="",
                manager=self.manager,
                container=self.list_scroll,
            )
            budget_lbl = UILabel(
                relative_rect=pygame.Rect(col_x[3], y_pos, col_w[3], row_h),
                text="",
                manager=self.manager,
                container=self.list_scroll,
            )

            self.row_labels.append([name_lbl, avg_lbl, peak_lbl, budget_lbl])
            y_pos += row_h + spacing

        self.list_scroll.set_scrollable_area_dimensions(
            (scroll_w, max(y_pos, self.list_scroll.rect.height))
        )

    def update(self, dt: float) -> None:
        """
        Updates profiler data, handles 5-second spike decay, and repopulates
        the UI tables. Called once per frame.

        Args:
            dt (float): Delta time.
        """
        if not self.world.debug_timing:
            if not self.container.visible:
                return

            # Profiling is disabled: reset bar and text
            disabled_text = "Profiling disabled. Click 'Profile: ON' to begin."
            if self.budget_label.text != disabled_text:
                self.budget_label.set_text(disabled_text)
            if self.bar_fill:
                self.bar_fill.kill()  # type: ignore[no-untyped-call]
                self.bar_fill = None

            # Fast clear using our row cache
            for idx, row in enumerate(self.row_labels):
                if self.row_systems[idx] != "" or self.row_hot_states[idx]:
                    self.row_systems[idx] = ""
                    self.row_hot_states[idx] = False
                    for lbl in row:
                        lbl.set_text("")
                        lbl.change_object_id(
                            ObjectID()
                        )  # type: ignore[no-untyped-call]
            return

        current_time = time.time()
        timings = self.world.get_system_timings()

        # 1. Decay logic & peak tracking
        for sys_name, avg_ms in timings.items():
            # Get current frame timing (max of rolling window or most recent)
            # Access World deques for spike peak tracking
            times_deque = self.world._system_timings.get(sys_name)
            current_frame_ms = times_deque[-1] if times_deque else avg_ms

            # Update peaks
            prev_peak = self.system_peaks.get(sys_name, 0.0)
            if current_frame_ms > prev_peak:
                self.system_peaks[sys_name] = current_frame_ms
                self.peak_timestamps[sys_name] = current_time
            else:
                # Decay peak if 5 seconds of inactivity passed
                last_update = self.peak_timestamps.get(sys_name, 0.0)
                if current_time - last_update > 5.0:
                    self.system_peaks[sys_name] = max(avg_ms, current_frame_ms)
                    self.peak_timestamps[sys_name] = current_time

        # If the container/tab is hidden, skip UI rendering entirely
        if not self.container.visible:
            return

        # Throttle UI updates to 5 times a second (0.2s interval)
        self.update_timer += dt
        if self.update_timer < 0.2:
            return
        self.update_timer = 0.0

        # 2. Total timing & Budget usage
        total_ms = sum(timings.values())
        pct = (total_ms / self.budget_ms) * 100.0
        label_text = (
            f"Frame Budget Usage: {total_ms:.2f}ms / {self.budget_ms:.2f}ms"
            f" ({pct:.1f}%)"
        )
        if self.budget_label.text != label_text:
            self.budget_label.set_text(label_text)

        # Update graphical budget progress bar
        bar_w = self.bar_bg.rect.width - 2
        fill_w = max(0, min(bar_w, int(bar_w * (total_ms / self.budget_ms))))
        bar_h = self.bar_bg.rect.height - 2

        # Recreate fill panel to dynamically color code
        fill_pct = total_ms / self.budget_ms
        if fill_pct > 1.0:
            c_id = "budget_red"
        elif fill_pct > 0.7:
            c_id = "budget_yellow"
        else:
            c_id = "budget_green"

        if not self.bar_fill:
            self.bar_fill = UIPanel(
                relative_rect=pygame.Rect(1, 1, fill_w, bar_h),
                manager=self.manager,
                container=self.bar_bg,
                object_id=ObjectID(class_id=c_id),
            )
            self.bar_fill_color = c_id
        else:
            if self.bar_fill.rect.width != fill_w:
                self.bar_fill.set_dimensions((fill_w, bar_h))
            # Only change class/color if it changed
            if self.bar_fill_color != c_id:
                self.bar_fill.change_object_id(ObjectID(class_id=c_id))
                self.bar_fill_color = c_id

        # 3. Populate rows in descending order
        sorted_systems = sorted(
            timings.items(), key=lambda x: x[1], reverse=True
        )

        for idx, row in enumerate(self.row_labels):
            if idx < len(sorted_systems):
                sys_name, avg_ms = sorted_systems[idx]
                peak_ms = self.system_peaks.get(sys_name, avg_ms)
                sys_pct = (avg_ms / self.budget_ms) * 100.0
                is_hot = (sys_pct > 15.0)

                avg_str = f"{avg_ms:.3f}"
                peak_str = f"{peak_ms:.3f}"
                pct_str = f"{sys_pct:.1f}%"

                # Update labels (only if text changes)
                if row[0].text != sys_name:
                    row[0].set_text(sys_name)
                if row[1].text != avg_str:
                    row[1].set_text(avg_str)
                if row[2].text != peak_str:
                    row[2].set_text(peak_str)
                if row[3].text != pct_str:
                    row[3].set_text(pct_str)

                # Only change object ID if state changed
                if (
                    self.row_systems[idx] != sys_name
                    or self.row_hot_states[idx] != is_hot
                ):
                    self.row_systems[idx] = sys_name
                    self.row_hot_states[idx] = is_hot
                    hot_id = (
                        ObjectID(class_id="system_hot")
                        if is_hot
                        else ObjectID()
                    )
                    for lbl in row:
                        lbl.change_object_id(
                            hot_id
                        )  # type: ignore[no-untyped-call]
            else:
                # Empty rows
                if self.row_systems[idx] != "" or self.row_hot_states[idx]:
                    self.row_systems[idx] = ""
                    self.row_hot_states[idx] = False
                    for lbl in row:
                        lbl.set_text("")
                        lbl.change_object_id(
                            ObjectID()
                        )  # type: ignore[no-untyped-call]

    def process_event(self, event: pygame.event.Event) -> bool:
        """
        Handles Pygame events dispatched from the main HUD loop.

        Args:
            event (pygame.event.Event): The Pygame event.

        Returns:
            bool: True if the event was consumed, False otherwise.
        """
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            # 1. Profile ON/OFF
            if event.ui_element == self.profile_btn:
                self.world.debug_timing = not self.world.debug_timing
                btn = self.profile_btn
                if self.world.debug_timing:
                    btn.select()  # type: ignore[no-untyped-call]
                    btn.set_text("Profile: ON")
                else:
                    btn.unselect()  # type: ignore[no-untyped-call]
                    btn.set_text("Profile: OFF")
                    self.system_peaks.clear()
                    self.peak_timestamps.clear()
                return True

            # 2. Toggle Target Frame budget
            elif event.ui_element == self.target_btn:
                if self.fps_target == 60:
                    self.fps_target = 30
                    self.budget_ms = 33.33
                    self.target_btn.set_text("Target: 30 FPS")
                else:
                    self.fps_target = 60
                    self.budget_ms = 16.67
                    self.target_btn.set_text("Target: 60 FPS")
                return True

            # 3. Reset Peaks
            elif event.ui_element == self.reset_peaks_btn:
                self.system_peaks.clear()
                self.peak_timestamps.clear()
                return True

        return False
