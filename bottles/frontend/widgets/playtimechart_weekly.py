from gettext import gettext as _
from typing import List, Optional, Any
from bottles.frontend.widgets.playtimechart_base import PlaytimeChartBase


class PlaytimeChartWeekly(PlaytimeChartBase):
    """
    A custom widget for rendering weekly playtime bar charts (7 days).

    Usage:
        chart = PlaytimeChartWeekly()
        chart.set_daily_data([120, 60, 180, ...])  # Minutes for each day (Sun-Sat)
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._bar_width = 40

    def set_daily_data(
        self, daily_data: List[int], max_hours: Optional[int] = None
    ) -> None:
        """
        Set the daily playtime data and render the chart.

        Args:
            daily_data: List of minutes for each day (Sunday to Saturday)
            max_hours: Optional maximum hours for grid. If None, calculated automatically.
        """
        self._data = daily_data
        self._render_chart()

    def _get_bottom_labels(self) -> List[str]:
        return [_("S"), _("M"), _("T"), _("W"), _("T"), _("F"), _("S")]
