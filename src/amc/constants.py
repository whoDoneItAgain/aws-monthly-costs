"""Constants used throughout the AWS Monthly Costs application."""

# Run mode types
RUN_MODE_ACCOUNT = "account"
RUN_MODE_ACCOUNT_DAILY = "account-daily"
RUN_MODE_BUSINESS_UNIT = "bu"
RUN_MODE_BUSINESS_UNIT_DAILY = "bu-daily"
RUN_MODE_SERVICE = "service"
RUN_MODE_SERVICE_DAILY = "service-daily"

VALID_RUN_MODES = [
    RUN_MODE_ACCOUNT,
    RUN_MODE_ACCOUNT_DAILY,
    RUN_MODE_BUSINESS_UNIT,
    RUN_MODE_BUSINESS_UNIT_DAILY,
    RUN_MODE_SERVICE,
    RUN_MODE_SERVICE_DAILY,
]

DEFAULT_RUN_MODES = [
    RUN_MODE_ACCOUNT,
    RUN_MODE_BUSINESS_UNIT,
    RUN_MODE_SERVICE,
]

# Output format types
OUTPUT_FORMAT_CSV = "csv"
OUTPUT_FORMAT_EXCEL = "excel"
OUTPUT_FORMAT_BOTH = "both"

VALID_OUTPUT_FORMATS = [
    OUTPUT_FORMAT_CSV,
    OUTPUT_FORMAT_EXCEL,
    OUTPUT_FORMAT_BOTH,
]

# Time period constants
TIME_PERIOD_MONTH = "month"
TIME_PERIOD_YEAR = "year"

# Year analysis requirements
MIN_MONTHS_FOR_YEAR_ANALYSIS = 24  # Two complete 12-month periods

# Cost aggregation keys
KEY_TOTAL = "total"
KEY_SHARED_SERVICES = "ss"

# AWS dimension keys
AWS_DIMENSION_LINKED_ACCOUNT = "LINKED_ACCOUNT"
AWS_DIMENSION_SERVICE = "SERVICE"

# Metrics
AWS_METRIC_UNBLENDED_COST = "UnblendedCost"

# Granularity
AWS_GRANULARITY_MONTHLY = "MONTHLY"
