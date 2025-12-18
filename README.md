# aws-monthly-costs

A tool to retrieve and report AWS monthly costs across accounts, business units, and services.

## Features

- Generate cost reports by account, business unit, or service
- Support for daily average cost calculations
- Export reports in **CSV** or **Excel** format (XLSX)
- Customizable cost aggregations and groupings
- Shared services cost allocation

## Installation

```bash
pip install -e .
```

## Usage

### Basic Usage

Generate cost reports in CSV format (default):

```bash
amc --profile your-aws-profile
```

### Excel Export

Generate cost reports in Excel format with styled headers:

```bash
amc --profile your-aws-profile --output-format excel
```

### Output Formats

The `--output-format` option allows you to choose between:
- `csv` (default): Generates CSV files
- `excel`: Generates Excel (XLSX) files with formatted headers and auto-adjusted columns

### Other Options

```bash
amc --profile your-aws-profile \
    --config-file path/to/config.yaml \
    --run-modes account bu service \
    --time-period previous \
    --output-format excel
```

Run `amc --help` for all available options.

## Output

Reports are generated in the `./outputs/` directory with filenames like:
- CSV format: `aws-monthly-costs-{run_mode}.csv`
- Excel format: `aws-monthly-costs-{run_mode}.xlsx`
