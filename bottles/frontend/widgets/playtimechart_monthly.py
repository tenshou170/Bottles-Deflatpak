from gettext import gettext as _
from typing import List, Optional, Any
from bottles.frontend.widgets.playtimechart_base import PlaytimeChartBase


class PlaytimeChartMonthly(PlaytimeChartBase):
    """
    A custom widget for rendering monthly playtime bar charts (yearly breakdown).

    Usage:
        chart = PlaytimeChartMonthly()
        chart.set_monthly_data([1200, 900, 1500, ...])  # Minutes for each month (Jan-Dec)
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._num_bars = 12

    def set_monthly_data(
        self, monthly_data: List[int], max_hours: Optional[int] = None
    ) -> None:
        """
        Set the monthly playtime data and render the chart.

        Args:
            monthly_data: List of minutes for each month (Jan=0, Feb=1, ..., Dec=11)
            max_hours: Optional maximum hours for grid. If None, calculated automatically.
        """
        self._data = monthly_data
        self._render_chart()

    def _get_bottom_labels(self) -> List[str]:
        return [
            _("J"),
            _("F"),
            _("M"),
            _("A"),
            _("M"),
            _("J"),
            _("J"),
            _("A"),
            _("S"),
            _("O"),
            _("N"),
            _("D"),
        ]

    def _get_grid_values(self) -> List[int]:
        return [
            0,
            self._chart_data["grid_max_hours"] // 2,
            self._chart_data["grid_max_hours"],
        ]

    def _should_show_grid_label(self, _val: int) -> bool:
        return True
