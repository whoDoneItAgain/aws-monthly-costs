"""Chart utilities for Excel reports.

This module provides common chart creation functions used across
Excel report generation to eliminate code duplication.
"""

from openpyxl.chart import PieChart, Reference
from openpyxl.chart.label import DataLabelList


def create_pie_chart(
    title=None,
    height=15,
    width=20,
    style=10,
    show_category_name=True,
    show_percentage=True,
    show_leader_lines=False,
    show_legend=True,
    show_series_name=False,
):
    """Create a configured pie chart.

    Args:
        title: Chart title (default: None for no title)
        height: Chart height (default: 15)
        width: Chart width (default: 20)
        style: Chart style number (default: 10)
        show_category_name: Whether to show category names on slices
        show_percentage: Whether to show percentages on slices
        show_leader_lines: Whether to show leader lines
        show_legend: Whether to show legend (default: True)
        show_series_name: Whether to show series name on labels (default: False)

    Returns:
        Configured PieChart object
    """
    chart = PieChart()
    chart.title = title
    chart.style = style
    chart.height = height
    chart.width = width

    # Configure data labels
    chart.dataLabels = DataLabelList()
    chart.dataLabels.showCatName = show_category_name
    chart.dataLabels.showPercent = show_percentage
    chart.dataLabels.showLeaderLines = show_leader_lines
    chart.dataLabels.showVal = False  # Don't show raw values
    chart.dataLabels.showSerName = show_series_name

    # Configure legend
    if not show_legend:
        chart.legend = None

    return chart


def add_data_to_pie_chart(chart, worksheet, data_col, label_col, start_row, end_row):
    """Add data and labels to a pie chart.

    Args:
        chart: PieChart object to add data to
        worksheet: Worksheet containing the data
        data_col: Column number for data values
        label_col: Column number for labels
        start_row: Starting row number
        end_row: Ending row number

    Returns:
        The chart with data added
    """
    labels = Reference(worksheet, min_col=label_col, min_row=start_row, max_row=end_row)
    data = Reference(worksheet, min_col=data_col, min_row=start_row, max_row=end_row)

    chart.add_data(data, titles_from_data=False)
    chart.set_categories(labels)

    return chart


def add_chart_to_worksheet(worksheet, chart, anchor_cell):
    """Add a chart to a worksheet at specified position.

    Modifies the worksheet in place by adding the chart.

    Args:
        worksheet: Worksheet to add chart to
        chart: Chart object to add
        anchor_cell: Cell address for top-left corner of chart (e.g., "H3")

    Returns:
        None (modifies worksheet in place)
    """
    worksheet.add_chart(chart, anchor_cell)
