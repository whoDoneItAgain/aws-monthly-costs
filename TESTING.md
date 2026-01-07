# Testing Guide

## Quick Start

### Run All Tests
```bash
tox
```

### Run Tests with Coverage Report
```bash
tox -e py312
# View HTML coverage report
open htmlcov/index.html
```

## Test Results

✅ **225 tests passing** - **UPDATED 2026-01-07**
- 200+ unit tests
- 17 integration tests  
- 7 end-to-end tests

📊 **95% code coverage** - **UPDATED 2026-01-07**
- Core business logic: 100%
- Main entry point: 99%
- Report export: 93%
- All calculator modules: 100%

**Why 95% and not 100%?** See [TEST_COVERAGE_ANALYSIS.md](TEST_COVERAGE_ANALYSIS.md) for detailed explanation of the remaining 5%.

## What's Tested

### ✅ Core Functionality
- AWS Cost Explorer integration
- Account, Business Unit, and Service cost calculations
- Daily average calculations with leap year support
- Shared services allocation
- CSV and Excel report generation
- Configuration validation
- Time period parsing

### ✅ Edge Cases
- Leap year February (29 vs 28 days)
- Cross-year boundaries (Dec → Jan)
- Zero costs and empty data
- Missing accounts/services
- AWS API pagination
- Large cost values
- Proper rounding

### ✅ Error Handling
- Invalid configurations
- Missing files
- Invalid AWS credentials
- Malformed input

### ✅ Regression Prevention
All bugs fixed by previous agents are now covered:
- Time period parsing bug
- Year calculation bug (leap years)
- Difference calculation (signed values)
- Percentage calculation (zero baseline)
- Configuration validation

## Test Organization

```
tests/
├── README.md              # Detailed test documentation
├── conftest.py           # Shared fixtures
├── test_main.py          # Main module tests (32 tests)
├── test_account.py       # Account runmode tests (14 tests)
├── test_bu.py            # Business unit tests (15 tests)
├── test_service.py       # Service runmode tests (18 tests)
├── test_constants.py     # Constants tests (10 tests)
├── test_reportexport.py  # Export tests (11 tests)
├── test_integration.py   # Integration tests (12 tests)
└── test_year_mode.py     # Year analysis tests (16 tests)
```

## Running Specific Tests

```bash
# Run specific file
pytest tests/test_main.py -v

# Run specific test class
pytest tests/test_main.py::TestParseArguments -v

# Run specific test
pytest tests/test_main.py::TestParseArguments::test_parse_arguments_with_profile -v

# Run with keyword filter
pytest tests/ -k "leap_year" -v
```

## Test Configuration

Tests use **tox** for automation:
- Isolated virtual environments
- Automatic dependency installation
- Coverage reporting (terminal + HTML)
- Consistent test execution

See `tox.ini` for configuration details.

## Writing New Tests

See `tests/README.md` for comprehensive guidelines on:
- Test naming conventions
- AAA pattern (Arrange, Act, Assert)
- Adding fixtures
- Mock usage
- Best practices

## CI/CD Integration

Tests are designed for CI/CD:
- ✅ Fast execution (< 2 seconds)
- ✅ No external dependencies (all mocked)
- ✅ Deterministic results
- ✅ Clear failure messages

## Need Help?

- See `tests/README.md` for detailed documentation
- Check `AGENT_HANDOFF.md` for test coverage summary
- Review existing tests for examples
