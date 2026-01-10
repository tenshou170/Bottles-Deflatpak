from typing import List, Optional, Any
from bottles.frontend.widgets.playtimechart_base import PlaytimeChartBase


class PlaytimeChartHourly(PlaytimeChartBase):
    """
    A custom widget for rendering hourly playtime bar charts (24-hour breakdown).

    Usage:
        chart = PlaytimeChartHourly()
        chart.set_hourly_data([120, 60, 180, ...])  # Minutes for each hour (0-23)
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._num_bars = 24

    def set_hourly_data(
        self, hourly_data: List[int], max_hours: Optional[int] = None
    ) -> None:
        """
        Set the hourly playtime data and render the chart.

        Args:
            hourly_data: List of minutes for each hour (0-23, where 0 = 00:00-00:59, etc.)
            max_hours: Optional maximum hours for grid. If None, calculated automatically.
        """
        self._data = hourly_data
        self._render_chart()

    def _get_grid_max(self) -> tuple[int, int]:
        return 60, 1

    def _get_grid_values(self) -> List[int]:
        return [0, 15, 30, 45, 60]

    def _get_grid_val_max(self) -> int:
        return 60

    def _format_grid_label(self, val: int) -> str:
        return f"{val}m"

    def _should_show_grid_label(self, _val: int) -> bool:
        return True

    def _get_bottom_labels(self) -> List[str]:
        labels = [""] * 24
        for h in [1, 6, 12, 18, 24]:
            labels[h - 1] = f"{h}h"
        return labels

    def _get_font_size_labels(self) -> int:
        return 9
