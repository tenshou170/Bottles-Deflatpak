# playtimechart_base.py
#
# Abstract base class for playtime chart widgets.

import math
from typing import List, Dict, Any, Tuple
from gi.repository import Gtk, Adw
from bottles.frontend.utils.playtime import PlaytimeService


class PlaytimeChartBase(Gtk.Box):
    """
    Abstract base class for playtime chart widgets.
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, **kwargs)

        self._data: List[int] = []
        self._chart_data: Dict[str, Any] = {}
        self._hover_x: float = 0
        self._hover_y: float = 0

        self._chart_height: int = 200
        self._bar_width: int = 40
        self._label_area_width: int = 48
        self._last_width: int = 0
        self._num_bars: int = 0

        self._build_ui()

        # Monitor widget allocation changes
        self.connect("notify::default-width", self._on_width_changed)

        # Monitor theme changes to update colors
        style_manager = Adw.StyleManager.get_default()
        style_manager.connect("notify::dark", self._on_style_changed)
        style_manager.connect("notify::accent-color", self._on_style_changed)

    def _get_font_scale(self) -> float:
        """Get the current font scale factor from GTK settings."""
        settings = Gtk.Settings.get_default()
        if settings:
            scale = settings.get_property("gtk-xft-dpi") / 96.0 / 1024.0
            return max(scale, 0.8)
        return 1.0

    def _on_width_changed(self, *_args: Any) -> None:
        """Re-render chart when widget width changes."""
        current_width = self.get_width()
        if current_width > 1 and current_width != self._last_width and self._data:
            self._render_chart()

    def _on_style_changed(self, *_args: Any) -> None:
        """Re-render chart when theme/style changes."""
        if hasattr(self, "_chart_box"):
            chart_area = self._chart_box.get_first_child()
            if chart_area:
                chart_area.queue_draw()
        if hasattr(self, "_labels_area"):
            self._labels_area.queue_draw()

    def _build_ui(self) -> None:
        """Build the chart UI structure."""
        self._chart_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self._chart_box.set_spacing(8)
        self._chart_box.set_vexpand(True)
        self.append(self._chart_box)

        self._labels_area = Gtk.DrawingArea()
        self._labels_area.set_content_height(20)
        self._labels_area.set_draw_func(self._draw_bottom_labels)
        self._labels_area.set_hexpand(True)
        self.append(self._labels_area)

    def _render_chart(self) -> None:
        """Render the bar chart with the current data."""
        while child := self._chart_box.get_first_child():
            self._chart_box.remove(child)

        if not self._data:
            return

        grid_max_minutes, grid_max_hours = self._get_grid_max()

        # Dynamic chart sizing
        container_width = self.get_width()
        if container_width <= 1:
            container_width = 614

        self._last_width = container_width

        num_bars = self._num_bars or len(self._data)
        available_chart_width = container_width - self._label_area_width

        # Calculate layout
        bar_width, spacing, start_x = self._calculate_layout(
            available_chart_width, num_bars
        )

        # Store chart data
        self._chart_data = {
            "data": self._data,
            "grid_max_hours": grid_max_hours,
            "grid_max_minutes": grid_max_minutes,
            "bar_positions": [],
            "label_area_width": self._label_area_width,
            "chart_width": available_chart_width,
            "spacing": spacing,
            "start_x": start_x,
            "bar_width": bar_width,
        }

        for i in range(num_bars):
            x = start_x + (i * (bar_width + spacing))
            self._chart_data["bar_positions"].append((x, bar_width))

        # Create drawing area
        chart_area = Gtk.DrawingArea()
        chart_area.set_content_height(self._chart_height)
        chart_area.set_draw_func(self._draw_chart)
        chart_area.set_hexpand(True)
        chart_area.set_has_tooltip(True)
        chart_area.connect("query-tooltip", self._on_chart_tooltip)

        motion_controller = Gtk.EventControllerMotion()
        motion_controller.connect("motion", self._on_chart_motion)
        chart_area.add_controller(motion_controller)

        self._chart_box.append(chart_area)

    def _calculate_layout(
        self, available_width: float, num_bars: int
    ) -> Tuple[int, float, float]:
        """Calculate bar width, spacing and start_x. Subclasses can override."""
        min_padding = 40
        min_spacing = 4
        usable_width = available_width - (2 * min_padding)

        bar_width = self._bar_width
        spacing = (
            (usable_width - (num_bars * bar_width)) / (num_bars - 1)
            if num_bars > 1
            else 0
        )
        spacing = max(spacing, min_spacing)

        total_bars_width = (num_bars * bar_width) + ((num_bars - 1) * spacing)
        start_x = (available_width - total_bars_width) / 2

        return bar_width, spacing, start_x

    def _get_grid_max(self) -> Tuple[int, int]:
        """Calculate grid max minutes and hours. Subclasses can override."""
        max_minutes = max(self._data) if any(self._data) else 1
        max_hours = max_minutes / 60.0
        grid_max_hours = max(2, math.ceil(max_hours / 2) * 2)
        return grid_max_hours * 60, grid_max_hours

    def _on_chart_motion(
        self, _controller: Gtk.EventControllerMotion, x: float, y: float
    ) -> None:
        self._hover_x = x
        self._hover_y = y

    def _on_chart_tooltip(
        self,
        widget: Gtk.Widget,
        x: float,
        y: float,
        _keyboard_mode: bool,
        tooltip: Gtk.Tooltip,
    ) -> bool:
        if not self._chart_data:
            return False

        data = self._chart_data["data"]
        grid_max_minutes = self._chart_data["grid_max_minutes"]
        bar_positions = self._chart_data["bar_positions"]
        height = widget.get_height()

        for i, minutes in enumerate(data):
            if minutes > 0:
                bar_x, bar_width = bar_positions[i]
                bar_height = max((minutes / grid_max_minutes) * height, 4)
                bar_y = height - bar_height
                if bar_x <= x <= bar_x + bar_width and bar_y <= y <= height:
                    tooltip.set_text(PlaytimeService.format_playtime(minutes * 60))
                    return True
        return False

    def _draw_bottom_labels(
        self, _area: Gtk.DrawingArea, ctx: Any, _width: float, height: float
    ) -> None:
        if not self._chart_data or "bar_positions" not in self._chart_data:
            return

        labels = self._get_bottom_labels()
        bar_positions = self._chart_data["bar_positions"]

        ctx.set_source_rgba(*self._get_color("foreground", 0.7))
        ctx.select_font_face("", 0, 0)
        ctx.set_font_size(self._get_font_size_labels() * self._get_font_scale())

        for i, (x, bar_width) in enumerate(bar_positions):
            if i < len(labels) and labels[i]:
                text = labels[i]
                extents = ctx.text_extents(text)
                ctx.move_to(
                    x + (bar_width - extents.width) / 2, height / 2 + extents.height / 2
                )
                ctx.show_text(text)

    def _draw_chart(
        self, _area: Gtk.DrawingArea, ctx: Any, width: float, height: float
    ) -> None:
        if not self._chart_data:
            return

        # Measure label width
        grid_max_hours = self._chart_data["grid_max_hours"]
        ctx.set_font_size(10 * self._get_font_scale())
        max_label = f"{grid_max_hours}h"
        label_text_width = ctx.text_extents(max_label).width + 10

        # Draw grid
        ctx.set_source_rgba(*self._get_color("foreground", 0.25))
        ctx.set_line_width(1)

        grid_values = self._get_grid_values()
        grid_max = self._get_grid_val_max()
        grid_end_x = width - label_text_width

        for val in grid_values:
            y = height - (val / grid_max) * height
            ctx.move_to(0, y)
            ctx.line_to(grid_end_x, y)
            ctx.stroke()

        # Draw grid labels
        ctx.set_source_rgba(*self._get_color("foreground", 0.7))
        for val in grid_values:
            if self._should_show_grid_label(val):
                y = height - (val / grid_max) * height
                text = self._format_grid_label(val)
                ctx.move_to(grid_end_x, max(10, min(y + 4, height - 5)))
                ctx.show_text(text)

        # Draw bars
        ctx.set_source_rgba(*self._get_color("accent_bg_color", 1.0))
        for i, minutes in enumerate(self._chart_data["data"]):
            if minutes > 0:
                bar_x, bar_w = self._chart_data["bar_positions"][i]
                bar_h = max(
                    (minutes / self._chart_data["grid_max_minutes"]) * height, 4
                )
                self._draw_rounded_bar(ctx, bar_x, height - bar_h, bar_w, bar_h)

        # Average line
        avg = sum(self._data) / len(self._data) if self._data else 0
        if avg > 0:
            avg_y = height - (avg / self._chart_data["grid_max_minutes"]) * height
            ctx.set_source_rgba(*self._get_color("foreground", 0.6))
            ctx.set_line_width(2)
            ctx.set_dash([5, 5])
            ctx.move_to(0, avg_y)
            ctx.line_to(grid_end_x, avg_y)
            ctx.stroke()
            ctx.set_dash([])

    def _get_color(self, name: str, alpha: float) -> Tuple[float, float, float, float]:
        style_context = self.get_style_context()
        res, color = style_context.lookup_color(name)
        if res:
            return color.red, color.green, color.blue, alpha
        return (
            (0.5, 0.5, 0.5, alpha) if name == "foreground" else (0.6, 0.4, 0.8, alpha)
        )

    def _draw_rounded_bar(self, ctx, x, y, w, h, radius=5):
        ctx.new_sub_path()
        ctx.arc(x + radius, y + radius, radius, 3.14159, 3.14159 * 1.5)
        ctx.arc(x + w - radius, y + radius, radius, 3.14159 * 1.5, 0)
        ctx.line_to(x + w, y + h)
        ctx.line_to(x, y + h)
        ctx.close_path()
        ctx.fill()

    def _get_bottom_labels(self) -> List[str]:
        return []

    def _get_grid_values(self) -> List[int]:
        return list(range(self._chart_data["grid_max_hours"] + 1))

    def _get_grid_val_max(self) -> int:
        return self._chart_data["grid_max_hours"]

    def _format_grid_label(self, val: int) -> str:
        return f"{val}h"

    def _should_show_grid_label(self, val: int) -> bool:
        return val % 2 == 0

    def _get_font_size_labels(self) -> int:
        return 10
