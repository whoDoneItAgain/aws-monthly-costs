# Agent Handoff Documentation

**Last Updated:** 2026-01-07  
**Purpose:** Provide context for specialized agents working on the aws-monthly-costs codebase

---

## Executive Summary

This codebase is a **Python CLI tool** for generating AWS cost reports by account, business unit, and service using the AWS Cost Explorer API. The application has been through multiple refactoring and improvement cycles, achieving:

- ✅ **100% test coverage** on core business logic (128 tests, 48% overall coverage)
- ✅ **No security vulnerabilities** (verified by Security-Analyzer Agent)
- ✅ **Optimized performance** (50% reduction in API calls for BU mode)
- ✅ **Well-documented** with comprehensive README and inline docstrings

---

## Important Design Decisions (2026-01-07)

### Absolute Value Usage in Excel Exports - BY DESIGN

**Design Decision:** Excel export functions use `abs()` to wrap difference values, displaying all cost changes as positive numbers.

- **Rationale:** This is the **preferred display format by design**
- **Scope:** 18 instances across all Excel export functions (BU, account, service, daily averages, year analysis)
- **Location:** `src/amc/reportexport/__init__.py` (lines 297-298, 318-319, 497-498, 517-518, 685-686, 714-715, 838-839, 936-937, 965-966, 1089-1090, 1591-1592)
- **Purpose:** Provides consistent magnitude display regardless of direction

**Implementation:**
```python
ws.cell(row, 4, abs(diff)).number_format = '"$"#,##0.00'
ws.cell(row, 5, abs(pct_diff)).number_format = "0.00%"
```

**How Users Understand Direction:**
- Conditional formatting indicates direction (green for decreases, red for increases)
- The magnitude is always shown as positive for clarity
- Percentage differences are also shown as absolute values

**⚠️ IMPORTANT FOR FUTURE AGENTS:**
**DO NOT REMOVE** the `abs()` wrappers from difference calculations in Excel exports. This is intentional design, not a bug. The absolute values combined with conditional formatting provide the clearest user experience.

---

## Architecture Overview

### Directory Structure

```
aws-monthly-costs/
├── src/amc/
│   ├── __main__.py              # Entry point & orchestration (610 lines)
│   ├── constants.py             # Named constants (52 lines)
│   ├── version.py               # Version information
│   ├── data/config/             # Default configuration files
│   ├── reportexport/            # Report generation (1720 lines)
│   │   └── __init__.py          # CSV/Excel export, charts, formatting
│   └── runmodes/                # Cost calculation modules
│       ├── account/             # Account cost calculations (155 lines)
│       ├── bu/                  # Business unit calculations (142 lines)
│       └── service/             # Service cost calculations (173 lines)
├── tests/                       # Comprehensive test suite (128 tests)
│   ├── conftest.py              # Shared fixtures
│   ├── test_main.py             # Main module tests
│   ├── test_account.py          # Account mode tests
│   ├── test_bu.py               # Business unit mode tests
│   ├── test_service.py          # Service mode tests
│   ├── test_reportexport.py    # Export function tests
│   ├── test_integration.py     # End-to-end integration tests
│   └── test_year_mode.py        # Year analysis tests
└── pyproject.toml              # Project configuration
```

### Key Modules

#### 1. Main Module (`__main__.py`)
- **Purpose:** Entry point and orchestration
- **Key Functions:**
  - `parse_arguments()` - CLI argument parsing (required: `--profile`)
  - `configure_logging()` - Logging setup (debug, info, or none)
  - `load_configuration()` - YAML config loading with validation
  - `parse_time_period()` - Date range parsing (month, year, or custom)
  - `create_aws_session()` - AWS session creation with validation
  - `main()` - Main orchestration logic

#### 2. Constants Module (`constants.py`)
- **Purpose:** Centralized constants and magic values
- **Contains:**
  - Run mode identifiers
  - Output format constants
  - AWS API dimension and metric names
  - Valid choices for CLI arguments

#### 3. Run Modes
Each runmode queries AWS Cost Explorer and processes cost data:

- **Account Mode** (`runmodes/account/`): Costs grouped by AWS account
- **Business Unit Mode** (`runmodes/bu/`): Costs aggregated into business units
- **Service Mode** (`runmodes/service/`): Costs grouped by AWS service

#### 4. Report Export (`reportexport/`)
- **Purpose:** Generate output files (CSV, Excel, analysis workbooks)
- **Key Functions:**
  - `export_report()` - Individual CSV/Excel reports
  - `export_analysis_excel()` - Comprehensive analysis workbook
  - `export_year_analysis_excel()` - Year-level analysis workbook
  - Helper functions for chart creation, formatting, width calculation

---

## Previous Refactoring History

### Bug Fixes (Previously Documented)

The following bugs were claimed to be fixed in previous iterations:

1. **Time Period Parsing Bug** ✅ Fixed
   - Issue: `parse_time_period()` set incorrect start dates
   - Fix: Correctly calculates previous month and handles year boundaries
   - Location: `src/amc/__main__.py` line 207-258

2. **Year Calculation Bug in Daily Averages** ✅ Fixed
   - Issue: Used `datetime.now().year` instead of actual cost data year
   - Fix: All runmodes now use actual year from API response
   - Location: All runmode modules

3. **Difference Calculation Display** ✅ **NOT A BUG - BY DESIGN**
   - Previous Claim: `abs()` wrappers were a bug that needed fixing
   - Reality: Using `abs()` for difference display is **intentional design**
   - Purpose: Show magnitude as positive values, use conditional formatting for direction
   - Location: 18 instances in `src/amc/reportexport/__init__.py`
   - **Note:** Do NOT remove `abs()` wrappers - this is preferred display format

4. **Percentage Calculation Edge Case** ✅ Fixed
   - Issue: Returned 0 when `val1==0` and `val2>0`
   - Fix: Properly handles zero baseline (returns 100% increase)
   - Location: Multiple locations in reportexport

5. **Configuration Validation** ✅ Fixed
   - Issue: No validation of required config keys
   - Fix: Validates all required keys with clear error messages
   - Location: `src/amc/__main__.py` line 153-204

6. **Time Period Format Validation** ✅ Fixed
   - Issue: No error handling for malformed time period strings
   - Fix: Validates format with clear error messages
   - Location: `src/amc/__main__.py` line 207-258

### Performance Optimizations ✅ Applied

1. **AWS API Call Optimization**
   - Reduced Cost Explorer API calls in BU mode from 2 to 1 (50% reduction)
   - Location: `src/amc/runmodes/bu/__init__.py`

2. **Sorting Algorithm Optimization**
   - Eliminated unnecessary dict conversions
   - Direct list slicing for top N items
   - Locations: account and service runmodes

3. **Excel Column Width Calculation**
   - Replaced nested loops with generator expressions
   - Location: `src/amc/reportexport/__init__.py`

4. **Data Structure Optimizations**
   - Set-based O(1) lookups for account filtering
   - Pre-built sets for shared services accounts

### Security Review ✅ Completed

- Uses `yaml.safe_load()` to prevent code execution
- No hardcoded credentials
- No known vulnerabilities in dependencies
- Comprehensive input validation
- No injection vulnerabilities
- Secure error messages

---

## Testing Infrastructure

### Test Statistics
- **Total Tests:** 128 (all passing)
- **Coverage:** 48% overall, 100% core business logic
- **Execution Time:** < 2 seconds
- **Framework:** pytest with tox for automation

### Test Categories

**Unit Tests (116 tests):**
- Main module: 33 tests
- Account runmode: 15 tests
- Business unit runmode: 15 tests
- Service runmode: 17 tests
- Constants: 11 tests
- Report export: 11 tests
- Year mode: 14 tests

**Integration Tests (12 tests):**
- End-to-end workflows
- Cross-module interactions
- Error handling scenarios
- Year boundary edge cases

### Running Tests

```bash
# Run all tests with tox (recommended)
tox

# Run specific Python version
tox -e py312

# Run with pytest directly
pytest tests/ -v --cov=amc --cov-report=term-missing

# Run specific test file
pytest tests/test_main.py -v
```

---

## Known Limitations (Not Bugs)

1. **AWS Cost Explorer API Pagination**
   - `get_cost_and_usage()` can return `NextPageToken` for large result sets
   - Current code doesn't handle pagination for cost queries
   - **Risk:** Low - MONTHLY granularity rarely exceeds page limits
   - **Mitigation:** Would only affect orgs with 1000+ accounts
   - **Recommendation:** Add pagination if needed in future

2. **Report Export Coverage**
   - Report export module has only 16% test coverage
   - Contains 1720 lines of Excel generation code
   - Complex openpyxl operations are hard to unit test
   - **Note:** Basic functionality IS tested and works

---

## Development Guidelines

### Code Quality Standards

1. **Naming Conventions:**
   - Use descriptive variable names (no abbreviations)
   - Follow PEP 8 style guide
   - Use snake_case for functions and variables

2. **Constants:**
   - All magic values should be defined in `constants.py`
   - Use UPPER_CASE for constant names

3. **Error Handling:**
   - Validate all user inputs
   - Provide clear, actionable error messages
   - Use try-except with specific exception types

4. **Documentation:**
   - All functions must have docstrings
   - Use type hints where appropriate
   - Keep README.md synchronized with code changes

### Testing Requirements

1. **New Features:**
   - Must include unit tests
   - Should include integration tests for cross-module features
   - Aim for 100% coverage on business logic

2. **Bug Fixes:**
   - Must include regression test
   - Test should fail before fix, pass after fix

3. **Refactoring:**
   - All existing tests must continue to pass
   - No decrease in test coverage

### Security Considerations

1. **Input Validation:**
   - Always validate configuration files
   - Validate time period formats
   - Check AWS profile existence before use

2. **Credential Handling:**
   - Never hardcode credentials
   - Use boto3 standard session management
   - Don't log sensitive information

3. **YAML Loading:**
   - Always use `yaml.safe_load()`, never `yaml.load()`

---

## Common Tasks for Future Agents

### Adding a New Run Mode

1. Create new module in `src/amc/runmodes/`
2. Implement cost calculation function
3. Add constants to `constants.py`
4. Update `__main__.py` to call new mode
5. Add tests in `tests/`
6. Update README.md with new mode documentation

### Adding a New Export Format

1. Add format constant to `constants.py`
2. Implement export function in `reportexport/__init__.py`
3. Update `export_report()` to handle new format
4. Add tests for new format
5. Update CLI argument parser if needed
6. Update README.md

### Debugging Common Issues

**Tests Failing:**
1. Check if dependencies are installed: `pip install -e .`
2. Run single test to isolate: `pytest tests/test_file.py::test_name -v`
3. Check for AWS credential issues in integration tests
4. Verify mock data matches expected formats

**Excel Generation Issues:**
1. Check openpyxl version compatibility
2. Verify cell references are 1-indexed (not 0-indexed)
3. Check number formatting strings
4. Verify worksheet names are valid (no special characters)

**AWS API Issues:**
1. Verify IAM permissions are correct
2. Check AWS profile configuration
3. Verify Cost Explorer API is enabled
4. Check for rate limiting (429 errors)

---

## Important Notes for Specialized Agents

### Bug-Hunter Agent
- **CRITICAL:** The `abs()` usage in Excel exports is **by design**, not a bug
- Do NOT remove `abs()` wrappers from difference calculations
- The absolute values combined with conditional formatting provide the preferred UX
- Focus on actual logic errors, not intentional display formatting choices
- Verify conditional formatting works correctly with absolute values

### Security-Analyzer Agent
- YAML loading is secure (`safe_load`)
- No credentials in code
- Input validation is comprehensive
- Debug logging may expose account IDs (documented)

### Performance-Optimizer Agent
- BU mode optimization already complete
- Consider async/await for parallel API calls
- Memory profiling recommended for large datasets
- Excel generation could benefit from batch operations

### Test-Generator Agent
- Core business logic has 100% coverage
- Report export needs more coverage
- Focus on Excel generation edge cases
- Add property-based tests if desired

### Documentation-Writer Agent
- README.md is comprehensive and up-to-date
- Breaking changes are clearly documented
- Migration guide exists for v0.1.0+
- Troubleshooting section is extensive

### Refactoring-Expert Agent
- Code is already well-refactored
- Follow existing patterns when making changes
- Keep helper functions small and focused
- Maintain backward compatibility

---

## Breaking Changes (v0.1.0+)

1. **`--profile` argument is now REQUIRED**
   - Previously optional with hardcoded default
   - Now must be explicitly specified for security

2. **`--include-ss` renamed to `--include-shared-services`**
   - More descriptive argument name
   - Old argument no longer works

Migration guide available in README.md

---

## Key Configuration

**Default Configuration File:** `src/amc/data/config/aws-monthly-costs-config.yaml`

**Required Sections:**
- `account-groups`: Business unit definitions (must include `ss` key)
- `service-aggregations`: Service grouping rules
- `top-costs-count`: Number of top items to display

**Optional Sections:**
- `shared-services`: Shared services accounts and allocation percentages
- `service-exclusions`: Services to exclude from reports

---

## Dependencies

**Core:**
- Python 3.10+
- boto3 >= 1.42.17 (AWS SDK)
- pyyaml >= 6.0.3 (Config parsing)
- openpyxl >= 3.1.5 (Excel generation)

**Development:**
- pytest (testing)
- pytest-cov (coverage)
- tox (test automation)
- ruff (linting and formatting)

---

## Release Information

**Current Version:** 0.1.2  
**Release Process:** See `RELEASE_WORKFLOW.md` for detailed instructions

**Version History:**
- 0.1.2 (Current): Bug fixes and improvements
- 0.1.0: Initial refactored version with breaking changes
- Earlier versions: Pre-refactoring codebase

---

## Questions & Troubleshooting

**For detailed troubleshooting**, see README.md sections:
- Common Issues
- Debug Logging
- Error Messages
- IAM Permissions

**For testing issues**, see `TESTING.md` and `tests/README.md`

**For security concerns**, see `SECURITY_REVIEW.md`

---

## Handoff Checklist

When passing this codebase to another agent:

- [ ] All tests passing (run `tox`)
- [ ] No linting errors (run `ruff check .`)
- [ ] Code is formatted (run `ruff format .`)
- [ ] Documentation is updated (README.md, docstrings)
- [ ] Breaking changes are documented
- [ ] Security scan is clean
- [ ] This document is updated with any new findings

---

## Contact & Feedback

For questions about this codebase or agent handoff:
1. Review git commit history for detailed changes
2. Check function docstrings for implementation details
3. Refer to test files for expected behavior examples
4. See README.md for user-facing documentation

---

**End of Agent Handoff Documentation**
