# aws-monthly-costs

A tool to retrieve and report AWS monthly costs across accounts, business units, and services.

## Features

- Generate cost reports by account, business unit, or service
- Support for daily average cost calculations
- Export reports in **CSV** and **Excel** format (XLSX) simultaneously (default)
- **Automatic analysis Excel file with charts** when all three data types are available
- Customizable cost aggregations and groupings
- Shared services cost allocation

## Installation

```bash
pip install -e .
```

## Usage

### Basic Usage

Generate cost reports in both CSV and Excel formats (default):

```bash
amc --profile your-aws-profile
```

This will create both `.csv` and `.xlsx` files for each run mode.

### Output Format Options

The `--output-format` option allows you to choose the output format:
- `both` (default): Generates both CSV and Excel files
- `csv`: Generates only CSV files
- `excel`: Generates only Excel (XLSX) files with formatted headers and auto-adjusted columns

### Generate Only CSV

```bash
amc --profile your-aws-profile --output-format csv
```

### Generate Only Excel

```bash
amc --profile your-aws-profile --output-format excel
```

### Other Options

```bash
amc --profile your-aws-profile \
    --config-file path/to/config.yaml \
    --run-modes account bu service \
    --time-period previous \
    --output-format both
```

Run `amc --help` for all available options.

## Output

Reports are generated in the `./outputs/` directory with filenames like:
- CSV format: `aws-monthly-costs-{run_mode}.csv`
- Excel format: `aws-monthly-costs-{run_mode}.xlsx`

By default, both formats are generated for each run mode.

### Analysis Excel File with Charts

When you run all three main modes (`account`, `bu`, and `service` - not the daily versions), an additional analysis file is automatically generated:
- **File**: `aws-monthly-costs-analysis.xlsx`
- **Content**: Interactive Excel workbook with formatted analysis tables and pie charts:
  - **Sheet1 (BU Costs)**: 
    - Monthly totals table (last 2 months comparison) starting at row 16
    - Daily average table (last 2 months comparison) starting at row 31
    - Shows difference, % difference, and % spend for each business unit
  - **Sheet2 (Top Services)**:
    - Monthly totals table for top 10 services starting at row 13
    - Daily average table for top 10 services starting at row 26
    - Pie chart showing distribution of top 10 services + "Other"
  - **Sheet3 (Top Accounts)**:
    - Monthly totals table for top 10 accounts starting at row 13
    - Daily average table for top 10 accounts starting at row 26
    - Pie chart showing distribution of top 10 accounts + "Other"
  - Formatted headers with bold text on light blue background (#D9E1F2)
  - Proper number formatting for currency and percentages
  
This file provides formatted analysis of your AWS spending patterns comparing the most recent 2 months.

**Example**: To generate the analysis file:
```bash
amc --profile your-aws-profile --run-modes account bu service
```
