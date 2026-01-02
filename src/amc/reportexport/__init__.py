import csv
import logging
from calendar import monthrange
from datetime import datetime

from openpyxl import Workbook
from openpyxl.chart import PieChart, Reference
from openpyxl.styles import Alignment, Font, PatternFill

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
    """Export analysis Excel file with formatted tables and pie charts.

    Creates analysis tables showing:
    - Monthly totals (last 2 months comparison)
    - Daily average (last 2 months comparison)
    - Pie charts for services and accounts (top 10 + Other)

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

    # Get last 2 months from the data - sort chronologically
    def get_month_num(month_str):
        try:
            return datetime.strptime(month_str, "%b").month
        except Exception:
            return 0

    months = sorted(list(bu_cost_matrix.keys()), key=get_month_num)
    if len(months) < 2:
        LOGGER.warning("Need at least 2 months of data for analysis")
        return

    last_2_months = months[-2:]

    # Create analysis sheets
    ws_bu = wb.create_sheet("Sheet1")
    _create_bu_analysis_tables(ws_bu, bu_cost_matrix, bu_group_list, last_2_months)

    ws_service = wb.create_sheet("Sheet2")
    _create_service_analysis_tables(
        ws_service,
        service_cost_matrix,
        service_group_list,
        last_2_months,
        bu_cost_matrix,
    )

    ws_account = wb.create_sheet("Sheet3")
    _create_account_analysis_tables(
        ws_account,
        account_cost_matrix,
        account_group_list,
        last_2_months,
        bu_cost_matrix,
    )

    # Ensure output directory exists
    output_file.parent.mkdir(parents=True, exist_ok=True)

    # Save the workbook
    wb.save(output_file)
    LOGGER.info(f"Analysis Excel file saved: {output_file}")


def _create_bu_analysis_tables(ws, cost_matrix, group_list, last_2_months):
    """Create BU analysis tables with monthly totals and daily average."""

    # Header formatting
    header_font = Font(bold=True, size=14, color="FF000000")
    header_fill = PatternFill(
        start_color="FFD9E1F2", end_color="FFD9E1F2", fill_type="solid"
    )
    header_alignment = Alignment(horizontal="center")

    # Monthly Totals section starting at A16
    row = 16
    ws.cell(row, 1, "Month").font = header_font
    ws.cell(row, 1).fill = header_fill
    ws.cell(row, 1).alignment = header_alignment

    ws.cell(row, 2, last_2_months[0]).font = header_font
    ws.cell(row, 2).fill = header_fill
    ws.cell(row, 2).alignment = header_alignment

    ws.cell(row, 3, last_2_months[1]).font = header_font
    ws.cell(row, 3).fill = header_fill
    ws.cell(row, 3).alignment = header_alignment

    ws.cell(row, 4, "Difference").font = header_font
    ws.cell(row, 4).fill = header_fill
    ws.cell(row, 4).alignment = header_alignment
    ws.cell(row, 4).number_format = '"$"#,##0.00'

    ws.cell(row, 5, "% Difference").font = header_font
    ws.cell(row, 5).fill = header_fill
    ws.cell(row, 5).alignment = header_alignment
    ws.cell(row, 5).number_format = "0.00%"

    ws.cell(row, 6, "% Spend").font = header_font
    ws.cell(row, 6).fill = header_fill
    ws.cell(row, 6).alignment = header_alignment

    # Data rows for monthly totals
    row += 1
    bus = list(group_list.keys())
    for bu in bus:
        ws.cell(row, 1, bu)

        val1 = cost_matrix[last_2_months[0]].get(bu, 0)
        val2 = cost_matrix[last_2_months[1]].get(bu, 0)
        diff = abs(val2 - val1)
        pct_diff = diff / val1 if val1 > 0 else 0
        pct_spend = val2 / cost_matrix[last_2_months[1]].get("total", 1)

        ws.cell(row, 2, val1).number_format = '"$"#,##0.00_);[Red]\\("$"#,##0.00\\)'
        ws.cell(row, 3, val2).number_format = '"$"#,##0.00_);[Red]\\("$"#,##0.00\\)'
        ws.cell(row, 4, diff).number_format = '"$"#,##0.00'
        ws.cell(row, 5, pct_diff).number_format = "0.00%"
        ws.cell(row, 6, pct_spend).number_format = "0.00%"

        row += 1

    # Total row
    total1 = cost_matrix[last_2_months[0]].get("total", 0)
    total2 = cost_matrix[last_2_months[1]].get("total", 0)
    diff = abs(total2 - total1)
    pct_diff = diff / total1 if total1 > 0 else 0

    ws.cell(row, 1, "total")
    ws.cell(row, 2, total1).number_format = '"$"#,##0.00_);[Red]\\("$"#,##0.00\\)'
    ws.cell(row, 3, total2).number_format = '"$"#,##0.00_);[Red]\\("$"#,##0.00\\)'
    ws.cell(row, 4, diff).number_format = '"$"#,##0.00'
    ws.cell(row, 5, pct_diff).number_format = "0.00%"
    ws.cell(row, 6, 1.0).number_format = "0.00%"

    # Daily Average section starting at A31
    row = 31
    ws.cell(row, 1, "Month").font = header_font
    ws.cell(row, 1).fill = header_fill
    ws.cell(row, 1).alignment = header_alignment

    ws.cell(row, 2, last_2_months[0]).font = header_font
    ws.cell(row, 2).fill = header_fill
    ws.cell(row, 2).alignment = header_alignment

    ws.cell(row, 3, last_2_months[1]).font = header_font
    ws.cell(row, 3).fill = header_fill
    ws.cell(row, 3).alignment = header_alignment

    ws.cell(row, 4, "Difference").font = header_font
    ws.cell(row, 4).fill = header_fill
    ws.cell(row, 4).alignment = header_alignment
    ws.cell(row, 4).number_format = '"$"#,##0.00'

    ws.cell(row, 5, "% Difference").font = header_font
    ws.cell(row, 5).fill = header_fill
    ws.cell(row, 5).alignment = header_alignment
    ws.cell(row, 5).number_format = "0.00%"

    # Calculate days in each month
    try:
        month1_date = datetime.strptime(last_2_months[0], "%b")
        month2_date = datetime.strptime(last_2_months[1], "%b")
        days1 = monthrange(datetime.now().year, month1_date.month)[1]
        days2 = monthrange(datetime.now().year, month2_date.month)[1]
    except Exception:
        # Fallback to 30 days if parsing fails
        days1 = days2 = 30

    # Data rows for daily average
    row += 1
    for bu in bus:
        ws.cell(row, 1, bu)

        val1 = cost_matrix[last_2_months[0]].get(bu, 0) / days1
        val2 = cost_matrix[last_2_months[1]].get(bu, 0) / days2
        diff = abs(val2 - val1)
        pct_diff = diff / val1 if val1 > 0 else 0

        ws.cell(row, 2, val1).number_format = '"$"#,##0.00_);[Red]\\("$"#,##0.00\\)'
        ws.cell(row, 3, val2).number_format = '"$"#,##0.00_);[Red]\\("$"#,##0.00\\)'
        ws.cell(row, 4, diff).number_format = '"$"#,##0.00'
        ws.cell(row, 5, pct_diff).number_format = "0.00%"

        row += 1

    # Total row for daily average
    total1_daily = cost_matrix[last_2_months[0]].get("total", 0) / days1
    total2_daily = cost_matrix[last_2_months[1]].get("total", 0) / days2
    diff = abs(total2_daily - total1_daily)
    pct_diff = diff / total1_daily if total1_daily > 0 else 0

    ws.cell(row, 1, "total")
    ws.cell(row, 2, total1_daily).number_format = '"$"#,##0.00_);[Red]\\("$"#,##0.00\\)'
    ws.cell(row, 3, total2_daily).number_format = '"$"#,##0.00_);[Red]\\("$"#,##0.00\\)'
    ws.cell(row, 4, diff).number_format = '"$"#,##0.00'
    ws.cell(row, 5, pct_diff).number_format = "0.00%"


def _create_service_analysis_tables(
    ws, cost_matrix, group_list, last_2_months, bu_cost_matrix
):
    """Create service analysis tables with monthly totals, daily average, and pie chart."""

    # Header formatting
    header_font = Font(bold=True, size=14, color="FF000000")
    header_fill = PatternFill(
        start_color="FFD9E1F2", end_color="FFD9E1F2", fill_type="solid"
    )
    header_alignment = Alignment(horizontal="center")

    # Get total from BU costs for % Spend calculation
    bu_total = bu_cost_matrix[last_2_months[1]].get("total", 1)

    # Get top 10 services by latest month cost
    service_costs = [
        (svc, cost_matrix[last_2_months[1]].get(svc, 0)) for svc in group_list
    ]
    service_costs.sort(key=lambda x: x[1], reverse=True)
    top_10_services = [svc for svc, _ in service_costs[:10]]

    # Calculate "Other" for pie chart
    top_10_total = sum(
        cost_matrix[last_2_months[1]].get(svc, 0) for svc in top_10_services
    )
    other_amount = bu_total - top_10_total

    # Monthly Totals section starting at A13
    row = 13
    ws.cell(row, 1, "Month").font = header_font
    ws.cell(row, 1).fill = header_fill
    ws.cell(row, 1).alignment = header_alignment

    ws.cell(row, 2, last_2_months[0]).font = header_font
    ws.cell(row, 2).fill = header_fill
    ws.cell(row, 2).alignment = header_alignment

    ws.cell(row, 3, last_2_months[1]).font = header_font
    ws.cell(row, 3).fill = header_fill
    ws.cell(row, 3).alignment = header_alignment

    ws.cell(row, 4, "Difference").font = header_font
    ws.cell(row, 4).fill = header_fill
    ws.cell(row, 4).alignment = header_alignment
    ws.cell(row, 4).number_format = '"$"#,##0.00'

    ws.cell(row, 5, "% Difference").font = header_font
    ws.cell(row, 5).fill = header_fill
    ws.cell(row, 5).alignment = header_alignment
    ws.cell(row, 5).number_format = "0.00%"

    ws.cell(row, 6, "% Spend").font = header_font
    ws.cell(row, 6).fill = header_fill
    ws.cell(row, 6).alignment = header_alignment

    # Data rows for monthly totals (top 10 only)
    row += 1
    for service in top_10_services:
        ws.cell(row, 1, service)

        val1 = cost_matrix[last_2_months[0]].get(service, 0)
        val2 = cost_matrix[last_2_months[1]].get(service, 0)
        diff = abs(val2 - val1)
        pct_diff = diff / val1 if val1 > 0 else 0
        pct_spend = val2 / bu_total

        ws.cell(row, 2, val1).number_format = '"$"#,##0.00_);[Red]\\("$"#,##0.00\\)'
        ws.cell(row, 3, val2).number_format = '"$"#,##0.00_);[Red]\\("$"#,##0.00\\)'
        ws.cell(row, 4, diff).number_format = '"$"#,##0.00'
        ws.cell(row, 5, pct_diff).number_format = "0.00%"
        ws.cell(row, 6, pct_spend).number_format = "0.00%"

        row += 1

    # Daily Average section starting at A26
    try:
        month1_date = datetime.strptime(last_2_months[0], "%b")
        month2_date = datetime.strptime(last_2_months[1], "%b")
        days1 = monthrange(datetime.now().year, month1_date.month)[1]
        days2 = monthrange(datetime.now().year, month2_date.month)[1]
    except Exception:
        days1 = days2 = 30

    row = 26
    ws.cell(row, 1, "Month").font = header_font
    ws.cell(row, 1).fill = header_fill
    ws.cell(row, 1).alignment = header_alignment

    ws.cell(row, 2, last_2_months[0]).font = header_font
    ws.cell(row, 2).fill = header_fill
    ws.cell(row, 2).alignment = header_alignment

    ws.cell(row, 3, last_2_months[1]).font = header_font
    ws.cell(row, 3).fill = header_fill
    ws.cell(row, 3).alignment = header_alignment

    ws.cell(row, 4, "Difference").font = header_font
    ws.cell(row, 4).fill = header_fill
    ws.cell(row, 4).alignment = header_alignment
    ws.cell(row, 4).number_format = '"$"#,##0.00'

    ws.cell(row, 5, "% Difference").font = header_font
    ws.cell(row, 5).fill = header_fill
    ws.cell(row, 5).alignment = header_alignment
    ws.cell(row, 5).number_format = "0.00%"

    # Data rows for daily average
    row += 1
    for service in top_10_services:
        ws.cell(row, 1, service)

        val1 = cost_matrix[last_2_months[0]].get(service, 0) / days1
        val2 = cost_matrix[last_2_months[1]].get(service, 0) / days2
        diff = abs(val2 - val1)
        pct_diff = diff / val1 if val1 > 0 else 0

        ws.cell(row, 2, val1).number_format = '"$"#,##0.00_);[Red]\\("$"#,##0.00\\)'
        ws.cell(row, 3, val2).number_format = '"$"#,##0.00_);[Red]\\("$"#,##0.00\\)'
        ws.cell(row, 4, diff).number_format = '"$"#,##0.00'
        ws.cell(row, 5, pct_diff).number_format = "0.00%"

        row += 1

    # Add pie chart for services (top 10 + Other)
    chart = PieChart()
    chart.title = "Top Services Distribution"
    chart.style = 10

    # Create data for pie chart - add top 10 + Other
    chart_start_row = 13

    # Add "Other" to chart data if significant
    if other_amount > 0:
        other_row = chart_start_row + 11
        ws.cell(other_row, 1, "Other")
        ws.cell(
            other_row, 3, other_amount
        ).number_format = '"$"#,##0.00_);[Red]\\("$"#,##0.00\\)'

        # Create chart including Other
        labels = Reference(
            ws, min_col=1, min_row=chart_start_row + 1, max_row=other_row
        )
        data = Reference(ws, min_col=3, min_row=chart_start_row, max_row=other_row)
    else:
        labels = Reference(
            ws,
            min_col=1,
            min_row=chart_start_row + 1,
            max_row=chart_start_row + 10,
        )
        data = Reference(
            ws, min_col=3, min_row=chart_start_row, max_row=chart_start_row + 10
        )

    chart.add_data(data, titles_from_data=True)
    chart.set_categories(labels)

    ws.add_chart(chart, "H13")


def _create_account_analysis_tables(
    ws, cost_matrix, group_list, last_2_months, bu_cost_matrix
):
    """Create account analysis tables with monthly totals, daily average, and pie chart."""

    # Header formatting
    header_font = Font(bold=True, size=14, color="FF000000")
    header_fill = PatternFill(
        start_color="FFD9E1F2", end_color="FFD9E1F2", fill_type="solid"
    )
    header_alignment = Alignment(horizontal="center")

    # Get total from BU costs for % Spend calculation
    bu_total = bu_cost_matrix[last_2_months[1]].get("total", 1)

    # Get top 10 accounts by latest month cost
    account_costs = [
        (acc, cost_matrix[last_2_months[1]].get(acc, 0)) for acc in group_list
    ]
    account_costs.sort(key=lambda x: x[1], reverse=True)
    top_10_accounts = [acc for acc, _ in account_costs[:10]]

    # Calculate "Other" for pie chart
    top_10_total = sum(
        cost_matrix[last_2_months[1]].get(acc, 0) for acc in top_10_accounts
    )
    other_amount = bu_total - top_10_total

    # Monthly Totals section starting at A13
    row = 13
    ws.cell(row, 1, "Month").font = header_font
    ws.cell(row, 1).fill = header_fill
    ws.cell(row, 1).alignment = header_alignment

    ws.cell(row, 2, last_2_months[0]).font = header_font
    ws.cell(row, 2).fill = header_fill
    ws.cell(row, 2).alignment = header_alignment

    ws.cell(row, 3, last_2_months[1]).font = header_font
    ws.cell(row, 3).fill = header_fill
    ws.cell(row, 3).alignment = header_alignment

    ws.cell(row, 4, "Difference").font = header_font
    ws.cell(row, 4).fill = header_fill
    ws.cell(row, 4).alignment = header_alignment
    ws.cell(row, 4).number_format = '"$"#,##0.00'

    ws.cell(row, 5, "% Difference").font = header_font
    ws.cell(row, 5).fill = header_fill
    ws.cell(row, 5).alignment = header_alignment
    ws.cell(row, 5).number_format = "0.00%"

    ws.cell(row, 6, "% Spend").font = header_font
    ws.cell(row, 6).fill = header_fill
    ws.cell(row, 6).alignment = header_alignment

    # Data rows for monthly totals (top 10 only)
    row += 1
    for account in top_10_accounts:
        ws.cell(row, 1, account)

        val1 = cost_matrix[last_2_months[0]].get(account, 0)
        val2 = cost_matrix[last_2_months[1]].get(account, 0)
        diff = abs(val2 - val1)
        pct_diff = diff / val1 if val1 > 0 else 0
        pct_spend = val2 / bu_total

        ws.cell(row, 2, val1).number_format = '"$"#,##0.00_);[Red]\\("$"#,##0.00\\)'
        ws.cell(row, 3, val2).number_format = '"$"#,##0.00_);[Red]\\("$"#,##0.00\\)'
        ws.cell(row, 4, diff).number_format = '"$"#,##0.00'
        ws.cell(row, 5, pct_diff).number_format = "0.00%"
        ws.cell(row, 6, pct_spend).number_format = "0.00%"

        row += 1

    # Daily Average section starting at A26
    try:
        month1_date = datetime.strptime(last_2_months[0], "%b")
        month2_date = datetime.strptime(last_2_months[1], "%b")
        days1 = monthrange(datetime.now().year, month1_date.month)[1]
        days2 = monthrange(datetime.now().year, month2_date.month)[1]
    except Exception:
        days1 = days2 = 30

    row = 26
    ws.cell(row, 1, "Month").font = header_font
    ws.cell(row, 1).fill = header_fill
    ws.cell(row, 1).alignment = header_alignment

    ws.cell(row, 2, last_2_months[0]).font = header_font
    ws.cell(row, 2).fill = header_fill
    ws.cell(row, 2).alignment = header_alignment

    ws.cell(row, 3, last_2_months[1]).font = header_font
    ws.cell(row, 3).fill = header_fill
    ws.cell(row, 3).alignment = header_alignment

    ws.cell(row, 4, "Difference").font = header_font
    ws.cell(row, 4).fill = header_fill
    ws.cell(row, 4).alignment = header_alignment
    ws.cell(row, 4).number_format = '"$"#,##0.00'

    ws.cell(row, 5, "% Difference").font = header_font
    ws.cell(row, 5).fill = header_fill
    ws.cell(row, 5).alignment = header_alignment
    ws.cell(row, 5).number_format = "0.00%"

    # Data rows for daily average
    row += 1
    for account in top_10_accounts:
        ws.cell(row, 1, account)

        val1 = cost_matrix[last_2_months[0]].get(account, 0) / days1
        val2 = cost_matrix[last_2_months[1]].get(account, 0) / days2
        diff = abs(val2 - val1)
        pct_diff = diff / val1 if val1 > 0 else 0

        ws.cell(row, 2, val1).number_format = '"$"#,##0.00_);[Red]\\("$"#,##0.00\\)'
        ws.cell(row, 3, val2).number_format = '"$"#,##0.00_);[Red]\\("$"#,##0.00\\)'
        ws.cell(row, 4, diff).number_format = '"$"#,##0.00'
        ws.cell(row, 5, pct_diff).number_format = "0.00%"

        row += 1

    # Add pie chart for accounts (top 10 + Other)
    chart = PieChart()
    chart.title = "Top Accounts Distribution"
    chart.style = 10

    # Create data for pie chart - add top 10 + Other
    chart_start_row = 13

    # Add "Other" to chart data if significant
    if other_amount > 0:
        other_row = chart_start_row + 11
        ws.cell(other_row, 1, "Other")
        ws.cell(
            other_row, 3, other_amount
        ).number_format = '"$"#,##0.00_);[Red]\\("$"#,##0.00\\)'

        # Create chart including Other
        labels = Reference(
            ws, min_col=1, min_row=chart_start_row + 1, max_row=other_row
        )
        data = Reference(ws, min_col=3, min_row=chart_start_row, max_row=other_row)
    else:
        labels = Reference(
            ws,
            min_col=1,
            min_row=chart_start_row + 1,
            max_row=chart_start_row + 10,
        )
        data = Reference(
            ws, min_col=3, min_row=chart_start_row, max_row=chart_start_row + 10
        )

    chart.add_data(data, titles_from_data=True)
    chart.set_categories(labels)

    ws.add_chart(chart, "H13")
