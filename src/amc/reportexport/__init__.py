import csv
import logging

from openpyxl import Workbook
from openpyxl.chart import AreaChart, BarChart, LineChart, PieChart, Reference
from openpyxl.styles import Font, PatternFill

LOGGER = logging.getLogger(__name__)


def exportreport(
    export_file, cost_matrix, group_list, group_by_type, output_format="csv"
):
    """Export cost report to CSV or Excel format.

    Args:
        export_file: Path to the output file
        cost_matrix: Dictionary containing cost data organized by month
        group_list: List or dictionary of groups (accounts, BUs, or services)
        group_by_type: Type of grouping ("account", "bu", or "service")
        output_format: Output format, either "csv" or "excel" (default: "csv")
    """
    # Directory should be created by caller, but ensure it exists
    export_file.parent.mkdir(parents=True, exist_ok=True)

    months = list(cost_matrix.keys())

    if output_format == "excel":
        _export_to_excel(export_file, cost_matrix, group_list, group_by_type, months)
    else:
        _export_to_csv(export_file, cost_matrix, group_list, group_by_type, months)


def _export_to_csv(export_file, cost_matrix, group_list, group_by_type, months):
    """Export cost report to CSV format."""
    csv_header = ["Month"] + months

    with open(export_file, "w", newline="") as ef:
        writer = csv.writer(ef)
        writer.writerow(csv_header)

        if group_by_type == "account":
            for account in group_list:
                csv_row = [account] + [
                    cost_matrix[month].get(account, 0) for month in months
                ]
                writer.writerow(csv_row)
        elif group_by_type == "bu":
            bus = list(group_list.keys()) + ["total"]
            for bu in bus:
                csv_row = [bu] + [cost_matrix[month].get(bu, 0) for month in months]
                writer.writerow(csv_row)
        elif group_by_type == "service":
            for service in group_list:
                csv_row = [service] + [
                    cost_matrix[month].get(service, 0) for month in months
                ]
                writer.writerow(csv_row)


def _export_to_excel(export_file, cost_matrix, group_list, group_by_type, months):
    """Export cost report to Excel format."""
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "AWS Costs"

    # Define styles for header
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(
        start_color="366092", end_color="366092", fill_type="solid"
    )

    # Write header
    header = ["Month"] + months
    for col_idx, header_value in enumerate(header, start=1):
        cell = worksheet.cell(row=1, column=col_idx, value=header_value)
        cell.font = header_font
        cell.fill = header_fill

    # Write data rows
    row_idx = 2
    if group_by_type == "account":
        for account in group_list:
            worksheet.cell(row=row_idx, column=1, value=account)
            for col_idx, month in enumerate(months, start=2):
                value = cost_matrix[month].get(account, 0)
                worksheet.cell(row=row_idx, column=col_idx, value=value)
            row_idx += 1
    elif group_by_type == "bu":
        bus = list(group_list.keys()) + ["total"]
        for bu in bus:
            worksheet.cell(row=row_idx, column=1, value=bu)
            for col_idx, month in enumerate(months, start=2):
                value = cost_matrix[month].get(bu, 0)
                worksheet.cell(row=row_idx, column=col_idx, value=value)
            row_idx += 1
    elif group_by_type == "service":
        for service in group_list:
            worksheet.cell(row=row_idx, column=1, value=service)
            for col_idx, month in enumerate(months, start=2):
                value = cost_matrix[month].get(service, 0)
                worksheet.cell(row=row_idx, column=col_idx, value=value)
            row_idx += 1

    # Auto-adjust column widths
    for column in worksheet.columns:
        max_length = 0
        column_letter = column[0].column_letter
        for cell in column:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except (AttributeError, TypeError):
                pass
        adjusted_width = min(max_length + 2, 50)
        worksheet.column_dimensions[column_letter].width = adjusted_width

    # Save workbook
    workbook.save(export_file)


def export_analysis_excel(
    output_file,
    bu_cost_matrix,
    bu_group_list,
    service_cost_matrix,
    service_group_list,
    account_cost_matrix,
    account_group_list,
):
    """Export analysis Excel file with charts (template-free implementation).

    Args:
        output_file: Path to the output analysis Excel file
        bu_cost_matrix: Dictionary containing BU cost data organized by month
        bu_group_list: Dictionary of BU groups
        service_cost_matrix: Dictionary containing service cost data organized by month
        service_group_list: List of services
        account_cost_matrix: Dictionary containing account cost data organized by month
        account_group_list: List of accounts
    """
    LOGGER.info(f"Creating analysis Excel file: {output_file}")

    # Create a new workbook
    wb = Workbook()
    wb.remove(wb.active)  # Remove default sheet

    # Create data sheets
    ws_bu = wb.create_sheet("aws-spend")
    _populate_data_sheet(ws_bu, bu_cost_matrix, bu_group_list, "bu")

    ws_service = wb.create_sheet("aws-spend-top-services")
    _populate_data_sheet(ws_service, service_cost_matrix, service_group_list, "service")

    ws_account = wb.create_sheet("aws-spend-top-accounts")
    _populate_data_sheet(ws_account, account_cost_matrix, account_group_list, "account")

    # Create analysis sheet with charts for BU data
    ws_chart = wb.create_sheet("Analysis - BU Costs")
    _create_bu_analysis_sheet(ws_chart, ws_bu)

    # Create analysis sheet for service costs
    ws_service_chart = wb.create_sheet("Analysis - Services")
    _create_service_analysis_sheet(ws_service_chart, ws_service)

    # Create analysis sheet for account costs
    ws_account_chart = wb.create_sheet("Analysis - Accounts")
    _create_account_analysis_sheet(ws_account_chart, ws_account)

    # Ensure output directory exists
    output_file.parent.mkdir(parents=True, exist_ok=True)

    # Save the workbook
    wb.save(output_file)
    LOGGER.info(f"Analysis Excel file saved: {output_file}")


def _create_bu_analysis_sheet(ws_chart, ws_data):
    """Create analysis sheet with charts for BU data."""
    # Add title
    ws_chart["A1"] = "Business Unit Cost Analysis"
    ws_chart["A1"].font = Font(bold=True, size=14)

    # Get data dimensions
    max_row = ws_data.max_row
    max_col = ws_data.max_column

    if max_row < 2:
        return

    # Create Area Chart
    chart1 = AreaChart()
    chart1.title = "BU Costs Over Time"
    chart1.style = 13
    chart1.y_axis.title = "Cost ($)"
    chart1.x_axis.title = "Month"

    # Data for chart (skip total row if present)
    last_row = max_row - 1 if ws_data.cell(max_row, 1).value == "total" else max_row
    data = Reference(ws_data, min_col=2, min_row=1, max_col=max_col, max_row=last_row)
    cats = Reference(ws_data, min_col=1, min_row=2, max_row=last_row)

    chart1.add_data(data, titles_from_data=True)
    chart1.set_categories(cats)

    ws_chart.add_chart(chart1, "A3")

    # Create Line Chart for trends
    chart2 = LineChart()
    chart2.title = "BU Cost Trends"
    chart2.style = 12
    chart2.y_axis.title = "Cost ($)"
    chart2.x_axis.title = "Month"

    chart2.add_data(data, titles_from_data=True)
    chart2.set_categories(cats)

    ws_chart.add_chart(chart2, "J3")


def _create_service_analysis_sheet(ws_chart, ws_data):
    """Create analysis sheet with charts for service data."""
    # Add title
    ws_chart["A1"] = "Top Services Cost Analysis"
    ws_chart["A1"].font = Font(bold=True, size=14)

    max_row = ws_data.max_row
    max_col = ws_data.max_column

    if max_row < 2:
        return

    # Create Bar Chart for services
    chart = BarChart()
    chart.type = "col"
    chart.style = 10
    chart.title = "Top Services by Cost"
    chart.y_axis.title = "Cost ($)"
    chart.x_axis.title = "Service"

    # Data for chart - last month column
    data = Reference(ws_data, min_col=max_col, min_row=1, max_row=max_row)
    cats = Reference(ws_data, min_col=1, min_row=2, max_row=max_row)

    chart.add_data(data, titles_from_data=True)
    chart.set_categories(cats)
    chart.shape = 4

    ws_chart.add_chart(chart, "A3")


def _create_account_analysis_sheet(ws_chart, ws_data):
    """Create analysis sheet with charts for account data."""
    # Add title
    ws_chart["A1"] = "Top Accounts Cost Analysis"
    ws_chart["A1"].font = Font(bold=True, size=14)

    max_row = ws_data.max_row
    max_col = ws_data.max_column

    if max_row < 2:
        return

    # Create Pie Chart for account distribution
    chart = PieChart()
    chart.title = "Cost Distribution by Account (Latest Month)"
    chart.style = 10

    # Data for chart - last month column
    labels = Reference(ws_data, min_col=1, min_row=2, max_row=max_row)
    data = Reference(ws_data, min_col=max_col, min_row=1, max_row=max_row)

    chart.add_data(data, titles_from_data=True)
    chart.set_categories(labels)

    ws_chart.add_chart(chart, "A3")


def _populate_data_sheet(worksheet, cost_matrix, group_list, group_by_type):
    """Populate a data sheet with cost data.

    Args:
        worksheet: openpyxl worksheet object
        cost_matrix: Dictionary containing cost data organized by month
        group_list: List or dictionary of groups
        group_by_type: Type of grouping ("account", "bu", or "service")
    """
    # Get months from cost matrix
    months = list(cost_matrix.keys())

    # Write header row
    header = ["Month"] + months
    for col_idx, header_value in enumerate(header, start=1):
        cell = worksheet.cell(row=1, column=col_idx, value=header_value)
        # Style header
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill(
            start_color="366092", end_color="366092", fill_type="solid"
        )

    # Write data rows
    row_idx = 2
    if group_by_type == "account":
        for account in group_list:
            worksheet.cell(row=row_idx, column=1, value=account)
            for col_idx, month in enumerate(months, start=2):
                value = cost_matrix[month].get(account, 0)
                worksheet.cell(row=row_idx, column=col_idx, value=value)
            row_idx += 1
    elif group_by_type == "bu":
        bus = list(group_list.keys()) + ["total"]
        for bu in bus:
            worksheet.cell(row=row_idx, column=1, value=bu)
            for col_idx, month in enumerate(months, start=2):
                value = cost_matrix[month].get(bu, 0)
                worksheet.cell(row=row_idx, column=col_idx, value=value)
            row_idx += 1
    elif group_by_type == "service":
        for service in group_list:
            worksheet.cell(row=row_idx, column=1, value=service)
            for col_idx, month in enumerate(months, start=2):
                value = cost_matrix[month].get(service, 0)
                worksheet.cell(row=row_idx, column=col_idx, value=value)
            row_idx += 1
