# Agent Handoff Documentation

This document provides context for specialized agents to review the refactored codebase.

## Refactoring Summary

The codebase has been comprehensively refactored following Python best practices:

### Key Changes
1. **Constants Module**: Created `src/amc/constants.py` with named constants
2. **Function Renaming**: All functions now have clear, descriptive names
3. **Variable Clarity**: Replaced abbreviations with full names
4. **Separation of Concerns**: Extracted 10+ helper functions from `main()`
5. **Documentation**: Added comprehensive docstrings
6. **Argument Parser**: Enhanced with better help text and made `--profile` required

### Breaking Changes
- `--profile` argument is now **required** (previously had a hardcoded default)
- `--include-ss` renamed to `--include-shared-services`

### Files Modified
- `src/amc/__main__.py` - Main entry point (major refactoring)
- `src/amc/constants.py` - New constants module
- `src/amc/reportexport/__init__.py` - Export functions
- `src/amc/runmodes/account/__init__.py` - Account cost calculations
- `src/amc/runmodes/bu/__init__.py` - Business unit cost calculations
- `src/amc/runmodes/service/__init__.py` - Service cost calculations

---

## 🐛 Bug-Hunter Agent Tasks

### Primary Focus Areas

1. **Time Period Parsing** (`parse_time_period()` in `__main__.py`)
   - Edge cases: year boundaries, invalid date formats
   - Potential issue: assumes start_date month=1 for "previous" mode
   
2. **AWS API Pagination** (`calculate_account_costs()` in `runmodes/account/__init__.py`)
   - Verify NextToken handling is complete
   - Check for potential infinite loops
   
3. **Cost Calculations** (all runmode modules)
   - Division by zero checks
   - Rounding consistency
   - Daily average calculation with different month lengths
   
4. **File I/O** (`export_report()` in `reportexport/__init__.py`)
   - Directory creation race conditions
   - File write error handling
   
5. **Configuration Loading** (`load_configuration()` in `__main__.py`)
   - Missing key handling
   - Invalid YAML format handling

### Questions to Address
- What happens if AWS returns zero accounts?
- How are negative costs handled?
- What if the config file is empty or missing required keys?
- Are there any timezone-related issues with date parsing?

---

## 🔒 Security-Analyzer Agent Tasks

### Primary Focus Areas

1. **Credentials & Authentication**
   - Review AWS profile handling
   - Check for credential leakage in logs
   - Validate STS session creation
   
2. **File Path Security**
   - Path traversal vulnerabilities in `--config-file` and `--aws-config-file`
   - Output directory creation security
   
3. **Input Validation**
   - Command-line argument validation
   - Configuration file schema validation
   - Time period string validation
   
4. **Logging Security**
   - Ensure sensitive data not logged
   - Review DEBUG level logging for credential exposure
   
5. **Dependencies**
   - Check for known vulnerabilities in:
     - boto3
     - pyyaml
     - openpyxl

### Questions to Address
- Could malicious config files cause code execution?
- Are there any injection vulnerabilities in file paths?
- Is the YAML loading using safe_load (not load)?
- Could debug logging expose AWS credentials?

---

## ⚡ Performance-Optimizer Agent Tasks

### Primary Focus Areas

1. **AWS API Calls**
   - Review pagination efficiency
   - Check for unnecessary duplicate calls
   - Consider batching opportunities
   
2. **Data Structures**
   - Cost matrix dictionary efficiency
   - List comprehension vs loops
   - Set usage for unique collections
   
3. **I/O Operations**
   - File writing efficiency
   - Excel generation optimization
   - Config file reading
   
4. **Memory Usage**
   - Large cost_matrix dictionaries
   - Account list accumulation
   - Potential memory leaks in loops
   
5. **Computation**
   - Daily average calculations
   - Sorting operations
   - Dictionary comprehensions

### Optimization Opportunities
- Can we reduce the number of Cost Explorer API calls?
- Should we cache account names?
- Can we parallelize any operations?
- Are there unnecessary data copies?

---

## 🧪 Test-Generator Agent Tasks

### Test Coverage Needed

1. **Unit Tests for Helper Functions**
   ```python
   # Test parse_arguments()
   # Test configure_logging()
   # Test load_configuration()
   # Test parse_time_period()
   # Test create_aws_session()
   # Test determine_output_formats()
   # Test generate_output_file_path()
   ```

2. **Integration Tests**
   - End-to-end run mode processing
   - AWS client mocking
   - File generation tests
   
3. **Edge Cases**
   - Empty account lists
   - Zero costs
   - Missing configuration keys
   - Invalid date formats
   - Leap years and month boundaries
   
4. **Error Handling Tests**
   - Invalid AWS profiles
   - Missing config files
   - Invalid time periods
   - API errors
   
5. **Regression Tests**
   - Ensure output matches previous version
   - Verify analysis Excel file generation

### Test Structure
- Use pytest framework (if available) or unittest
- Mock AWS API calls using moto or manual mocking
- Test both success and failure paths
- Include fixture data for realistic scenarios

---

## 📝 Documentation-Writer Agent Tasks

### Documentation Updates Needed

1. **README.md**
   - Update all command examples with new argument names
   - Document breaking changes (--profile now required)
   - Add migration guide from old to new CLI
   - Update --include-ss to --include-shared-services
   
2. **Usage Examples**
   ```bash
   # OLD (no longer works)
   amc --include-ss
   
   # NEW (required)
   amc --profile my-profile --include-shared-services
   ```
   
3. **Configuration Guide**
   - Document all config file options
   - Provide example configurations
   - Explain shared services allocation
   
4. **API Documentation**
   - Document all public functions
   - Explain function parameters
   - Provide usage examples
   
5. **Troubleshooting Guide**
   - Common error messages
   - AWS authentication issues
   - Configuration problems

### New Sections to Add
- **Breaking Changes** - Prominent warning about CLI changes
- **Migration Guide** - Step-by-step upgrade instructions
- **Architecture Overview** - Explain the module structure
- **Contributing Guide** - How to add new run modes or features

---

## Testing & Validation Checklist

Before finalizing, ensure:
- [ ] All agents have completed their reviews
- [ ] All identified bugs are fixed
- [ ] Security issues are resolved
- [ ] Performance optimizations are applied
- [ ] Tests are passing
- [ ] Documentation is updated
- [ ] Breaking changes are clearly documented
- [ ] Migration guide is provided

---

## Contact & Questions

For questions about the refactoring:
1. Review the git commits for detailed change history
2. Check function docstrings for implementation details
3. Refer to constants.py for all magic values
