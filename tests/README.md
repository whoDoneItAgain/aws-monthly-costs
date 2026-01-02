# Test Suite Documentation

This directory contains comprehensive unit and integration tests for the AWS Monthly Costs application.

## Test Structure

### Test Files

- **`test_main.py`** - Tests for the main module (`__main__.py`)
  - Argument parsing
  - Logging configuration
  - Configuration loading and validation
  - Time period parsing
  - AWS session creation
  - Output format determination
  - File path generation

- **`test_account.py`** - Tests for account runmode
  - Cost building from API responses
  - Cost matrix construction
  - Account cost calculations
  - Account name extraction
  - Edge cases (pagination, leap years, etc.)

- **`test_bu.py`** - Tests for business unit runmode
  - Cost building for BU aggregation
  - Shared services allocation
  - Daily average calculations
  - Edge cases (zero costs, missing accounts)

- **`test_service.py`** - Tests for service runmode
  - Service cost aggregation
  - Top service filtering
  - Service name extraction
  - Mixed aggregation scenarios

- **`test_constants.py`** - Tests for constants module
  - Validates all constant definitions
  - Ensures consistency across the application

- **`test_reportexport.py`** - Tests for report export functionality
  - CSV export validation
  - Excel export validation
  - Multiple formats and edge cases

- **`test_integration.py`** - Integration tests
  - End-to-end workflow tests
  - Cross-module interaction tests
  - Error handling scenarios
  - Year boundary edge cases
  - Shared services allocation integration

### Fixtures (`conftest.py`)

Shared test fixtures available to all tests:

- `mock_aws_session` - Mock AWS session
- `mock_cost_explorer_client` - Mock Cost Explorer client
- `mock_organizations_client` - Mock Organizations client
- `sample_account_list` - Sample account data
- `sample_cost_and_usage_response` - Sample API response
- `sample_config` - Sample configuration dictionary
- `sample_dates` - Sample date ranges
- `temp_output_dir` - Temporary output directory

## Running Tests

### Using Tox (Recommended)

Tox provides isolated test environments and is the recommended way to run tests:

```bash
# Run all tests
tox

# Run specific environment
tox -e py312

# Run with coverage report
tox -e py312
```

### Using Pytest Directly

```bash
# Run all tests
pytest tests/

# Run with verbose output
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=amc --cov-report=term-missing

# Run specific test file
pytest tests/test_main.py

# Run specific test class
pytest tests/test_main.py::TestParseArguments

# Run specific test
pytest tests/test_main.py::TestParseArguments::test_parse_arguments_with_profile
```

## Test Coverage

Current test coverage: **48%**

Coverage breakdown by module:
- `__main__.py`: 92%
- `constants.py`: 100%
- `runmodes/account`: 100%
- `runmodes/bu`: 100%
- `runmodes/service`: 100%
- `reportexport`: 16% (large module with complex Excel generation)

To view detailed coverage report:
```bash
tox -e py312
# Open htmlcov/index.html in a browser
```

## Test Categories

### Unit Tests (100 tests)

Test individual functions and classes in isolation with mocked dependencies:

- **Argument Parsing**: 8 tests
- **Logging**: 3 tests
- **Configuration**: 7 tests
- **Time Period Parsing**: 5 tests
- **AWS Session**: 3 tests
- **Output Formats**: 4 tests
- **File Paths**: 3 tests
- **Account Runmode**: 15 tests
- **BU Runmode**: 15 tests
- **Service Runmode**: 17 tests
- **Constants**: 11 tests
- **Report Export**: 10 tests

### Integration Tests (12 tests)

Test interaction between multiple components:

- End-to-end workflow tests
- File generation tests
- Error handling tests
- Cross-year boundary tests
- Shared services allocation tests

## Key Test Scenarios

### Edge Cases Covered

1. **Leap Years**: Tests verify correct day counts for February in leap vs non-leap years
2. **Year Boundaries**: Tests for December to January transitions
3. **Zero Costs**: Handling of accounts/services with no costs
4. **Empty Data**: Handling of empty account lists and missing data
5. **Missing Accounts**: Accounts in config but not in API response
6. **Pagination**: AWS API pagination handling
7. **Large Values**: Very large cost amounts
8. **Rounding**: Proper rounding of decimal values

### Error Handling Tested

1. Missing configuration files
2. Invalid YAML syntax
3. Missing required configuration keys
4. Invalid AWS profiles
5. Invalid AWS credentials
6. Malformed time period strings
7. Invalid date values

### Regression Prevention

The test suite validates all bugs fixed by previous agents:

1. **Time Period Parsing Bug** - Tests ensure correct previous month calculation
2. **Year Calculation Bug** - Tests verify actual year from cost data is used
3. **Difference Calculation** - Tests verify signed differences (not absolute)
4. **Percentage Calculation** - Tests handle zero baseline edge case
5. **Configuration Validation** - Tests ensure proper validation of all keys

## Writing New Tests

### Test Naming Convention

- Test files: `test_<module>.py`
- Test classes: `Test<Functionality>`
- Test methods: `test_<what_is_being_tested>`

### Test Structure (AAA Pattern)

```python
def test_example(self):
    """Test description."""
    # Arrange - Set up test data and mocks
    input_data = {"key": "value"}
    expected_output = {"result": "expected"}
    
    # Act - Execute the code being tested
    result = function_under_test(input_data)
    
    # Assert - Verify the results
    assert result == expected_output
```

### Adding Fixtures

Add shared fixtures to `conftest.py`:

```python
@pytest.fixture
def my_fixture():
    """Fixture description."""
    return {"data": "value"}
```

## Continuous Integration

Tests are designed to run in CI/CD pipelines:

- Fast execution (< 2 seconds for full suite)
- No external dependencies (all AWS calls mocked)
- Deterministic results (no random data)
- Clear failure messages

## Test Maintenance

### When to Update Tests

- When fixing bugs (add regression test)
- When adding new features
- When changing function signatures
- When deprecating functionality

### Test Quality Guidelines

1. **Independence**: Tests should not depend on each other
2. **Isolation**: Use mocks for external dependencies
3. **Clarity**: Clear test names and documentation
4. **Coverage**: Aim for high coverage of critical paths
5. **Maintainability**: Keep tests simple and readable

## Troubleshooting

### Common Issues

**Tests failing locally but passing in CI**
- Check Python version (requires 3.12+)
- Ensure all dependencies are installed
- Clear tox cache: `rm -rf .tox`

**Import errors**
- Install package in development mode: `pip install -e .`
- Check PYTHONPATH includes src directory

**Coverage not generating**
- Ensure pytest-cov is installed
- Check tox.ini configuration

## Additional Resources

- [pytest documentation](https://docs.pytest.org/)
- [tox documentation](https://tox.wiki/)
- [unittest.mock documentation](https://docs.python.org/3/library/unittest.mock.html)
