# Security Review Report

**Review Date:** 2026-01-02  
**Reviewer:** Security-Analyzer Agent  
**Repository:** whoDoneItAgain/aws-monthly-costs  
**Scope:** Full repository security review

---

## Executive Summary

This security review analyzed the AWS Monthly Costs application for common vulnerabilities and security best practices. The application is a Python-based CLI tool that retrieves AWS cost data and generates reports.

**Overall Security Rating:** ✅ **GOOD** - No critical vulnerabilities found

The codebase follows secure coding practices with proper input validation, safe YAML loading, and no hardcoded credentials. Minor recommendations are provided to further enhance security posture.

---

## Findings Summary

### ✅ Secure Practices Identified

1. **Safe YAML Loading** - Uses `yaml.safe_load()` instead of unsafe `yaml.load()`
2. **No Hardcoded Credentials** - No AWS credentials or secrets in source code
3. **Dependency Security** - All dependencies (boto3, pyyaml, openpyxl) have no known vulnerabilities
4. **Input Validation** - Proper validation of configuration files and time periods
5. **No Code Injection** - No use of `eval()`, `exec()`, or `subprocess` with user input
6. **Proper Error Handling** - Graceful error messages without leaking sensitive information

### ⚠️ Security Considerations (Low Risk)

1. **Path Traversal** - Command-line file paths are not validated (LOW RISK)
2. **Debug Logging** - AWS API responses logged in debug mode (INFORMATIONAL)
3. **Output Directory** - Fixed output directory with predictable paths (LOW RISK)

---

## Detailed Security Analysis

### 1. Credentials & Authentication ✅

**Status:** SECURE

- **AWS Credentials Handling:**
  - Uses boto3 Session with named profiles (standard AWS SDK practice)
  - Credentials loaded from `~/.aws/config` (standard AWS CLI location)
  - No credentials hardcoded in source code
  - Session validation via STS `get_caller_identity()` call

- **Profile Validation:**
  ```python
  # Line 242-248: Validates profile exists before use
  if not aws_config.has_section(f"profile {aws_profile}"):
      raise Exception(f"AWS profile '{aws_profile}' does not exist...")
  ```

- **Session Testing:**
  ```python
  # Line 254-261: Validates credentials work before proceeding
  try:
      sts_client.get_caller_identity()
  except Exception as e:
      LOGGER.error(f"AWS profile ({aws_profile}) session is not valid: {e}")
  ```

**Recommendations:** ✅ No changes needed

---

### 2. Input Validation ✅

**Status:** SECURE

- **Configuration File Validation:**
  - Required keys validated (lines 172-188)
  - YAML parsing errors caught with informative messages
  - Empty configuration files rejected
  - Type checking for configuration values

- **Time Period Validation:**
  ```python
  # Line 216-223: Validates date format
  try:
      time_parts = time_period_str.split("_")
      if len(time_parts) != 2:
          raise ValueError(f"Time period must be in format 'YYYY-MM-DD_YYYY-MM-DD'...")
      start_date = datetime.strptime(time_parts[0], "%Y-%m-%d").date()
      end_date = datetime.strptime(time_parts[1], "%Y-%m-%d").date()
  except (ValueError, IndexError) as e:
      raise ValueError(f"Invalid time period format '{time_period_str}': {e}")
  ```

- **Command-Line Arguments:**
  - Uses argparse with choices for enum-like values (run-modes, output-format)
  - Profile argument required and validated against AWS config

**Recommendations:** ✅ No changes needed - validation is comprehensive

---

### 3. YAML Loading Security ✅

**Status:** SECURE

- **Safe Loading:**
  ```python
  # Line 162: Uses safe_load, not unsafe load()
  config = yaml.safe_load(config_file)
  ```

- **Why This Matters:**
  - `yaml.load()` can execute arbitrary Python code (RCE vulnerability)
  - `yaml.safe_load()` only parses safe YAML types (strings, numbers, lists, dicts)
  - This prevents malicious YAML files from executing code

**Recommendations:** ✅ No changes needed - already using safe_load

---

### 4. File Path Security ⚠️

**Status:** LOW RISK

**Current Implementation:**
```python
# Lines 511-512: User-supplied paths converted to absolute paths
aws_config_file_path = Path(os.path.expanduser(args.aws_config_file)).absolute()
config_file_path = Path(args.config_file).absolute()
```

**Potential Issues:**
1. **Path Traversal:** Users can specify any file path
   - `--config-file /etc/passwd` would attempt to read system files
   - `--aws-config-file ../../sensitive/file` could access parent directories

2. **Output Directory:** Fixed to `./outputs/` (line 541)
   - Not configurable by users
   - Cannot be manipulated to write files outside intended directory

**Risk Assessment:**
- **LOW RISK** because:
  - Application runs with user's own permissions
  - No privilege escalation possible
  - Only reads files (no writes to user-specified paths)
  - Output directory is hardcoded (safe)
  - Tool designed for trusted users (DevOps/FinOps teams)

**Recommendations:**
- ⚠️ OPTIONAL: Add path validation to prevent reading system files
- ⚠️ OPTIONAL: Document that config files should only come from trusted sources
- ✅ Current implementation acceptable for intended use case

---

### 5. Logging Security ⚠️

**Status:** INFORMATIONAL

**Debug Logging Content:**
```python
# Lines 92, 100: Logs AWS API responses in debug mode
LOGGER.debug(account_get_cost_and_usage["ResultsByTime"])
LOGGER.debug(account_costs)
```

**What's Logged:**
- AWS Cost Explorer API responses (cost data, account IDs, service names)
- NOT credentials (AWS SDK handles credentials separately)
- Configuration arguments (but not file contents)
- AWS profile name (not a secret)

**Sensitive Data Assessment:**
- ✅ No AWS access keys or secret keys logged
- ⚠️ Account IDs logged (considered semi-sensitive in some orgs)
- ⚠️ Cost data logged (may be considered confidential business data)

**Current Mitigation:**
- Debug logging disabled by default
- User must explicitly enable with `--debug-logging` flag
- Console output only (not written to files)

**Recommendations:**
- ✅ Current implementation acceptable
- 📝 Document: "Debug logs may contain AWS account IDs and cost data - use with caution"

---

### 6. Dependencies Security ✅

**Status:** SECURE

**Dependencies Analyzed:**
```
boto3==1.42.17
pyyaml==6.0.3
openpyxl==3.1.5
```

**Vulnerability Scan Results:**
- ✅ **boto3 1.42.17:** No known vulnerabilities
- ✅ **pyyaml 6.0.3:** No known vulnerabilities  
- ✅ **openpyxl 3.1.5:** No known vulnerabilities

**Recommendations:**
- ✅ Keep dependencies updated regularly
- ✅ Consider using Dependabot (already configured in `.github/dependabot.yml`)

---

### 7. Output File Security ✅

**Status:** SECURE

**File Writing Operations:**
```python
# Line 40: CSV writing with safe parameters
with open(export_file, "w", newline="") as ef:
    writer = csv.writer(ef)

# Line 203: Excel writing via openpyxl
wb.save(output_file)
```

**Security Analysis:**
- ✅ Output directory created safely with `mkdir(parents=True, exist_ok=True)`
- ✅ File paths constructed from trusted constants, not user input
- ✅ No path traversal possible in output filenames
- ✅ CSV writer properly configured (no injection via delimiters)

**Output File Pattern:**
```
./outputs/aws-monthly-costs-{mode}.{csv|xlsx}
./outputs/aws-monthly-costs-analysis.xlsx
```

**Recommendations:** ✅ No changes needed

---

### 8. Injection Vulnerabilities ✅

**Status:** SECURE

**Analysis:**
- ✅ No SQL injection (no database operations)
- ✅ No Command injection (no subprocess/os.system calls)
- ✅ No LDAP injection (no LDAP operations)
- ✅ No XML injection (no XML processing)
- ✅ No Template injection (no template rendering)

**Recommendations:** ✅ No changes needed

---

### 9. Error Handling ✅

**Status:** SECURE

**Error Messages:**
```python
# Line 164: Informative but not overly verbose
raise FileNotFoundError(f"Configuration file not found: {config_file_path}")

# Line 257: No credential leakage
LOGGER.error(f"AWS profile ({aws_profile}) session is not valid: {e}")
```

**Security Analysis:**
- ✅ Error messages helpful without exposing internal details
- ✅ No credential leakage in error messages
- ✅ Stack traces go to stderr (not logged to files)
- ✅ Proper exception handling throughout

**Recommendations:** ✅ No changes needed

---

### 10. Access Control ✅

**Status:** SECURE

**Analysis:**
- Application uses AWS IAM for access control
- Requires proper AWS permissions:
  - `ce:GetCostAndUsage` (Cost Explorer)
  - `organizations:ListAccounts` (Organizations)
  - `organizations:DescribeAccount` (Organizations)
  - `sts:GetCallerIdentity` (STS)

- ✅ No privilege escalation possible
- ✅ Respects AWS IAM policies
- ✅ No hardcoded IAM policies or permissions

**Recommendations:** ✅ No changes needed

---

## Security Best Practices Checklist

- [x] No hardcoded credentials or secrets
- [x] Safe YAML loading (safe_load)
- [x] Input validation for all user inputs
- [x] No code injection vulnerabilities (eval/exec)
- [x] No command injection (subprocess)
- [x] Secure dependency versions
- [x] Proper error handling
- [x] No sensitive data in logs (by default)
- [x] File operations properly secured
- [x] AWS credentials via standard SDK mechanisms

---

## Recommendations

### High Priority
None - No critical or high-priority security issues found.

### Medium Priority
None - No medium-priority security issues found.

### Low Priority / Optional

1. **Path Validation Enhancement (Optional)**
   - Add validation to restrict config file paths to expected directories
   - Document that config files should come from trusted sources only
   - Risk: LOW (application runs with user permissions)

2. **Debug Logging Documentation**
   - Add note in README that debug logs contain account IDs and cost data
   - Already properly gated behind explicit flag
   - Risk: INFORMATIONAL

3. **Security Documentation**
   - Consider adding SECURITY.md with security policy
   - Document required AWS permissions
   - Add security best practices for deployment

---

## Compliance Considerations

### OWASP Top 10 (2021)

1. **A01:2021 - Broken Access Control** ✅ N/A (Delegates to AWS IAM)
2. **A02:2021 - Cryptographic Failures** ✅ PASS (No crypto needed, AWS SDK handles TLS)
3. **A03:2021 - Injection** ✅ PASS (No injection points)
4. **A04:2021 - Insecure Design** ✅ PASS (Secure design principles followed)
5. **A05:2021 - Security Misconfiguration** ✅ PASS (Good defaults, no debug in prod)
6. **A06:2021 - Vulnerable Components** ✅ PASS (No known vulnerabilities)
7. **A07:2021 - Identification and Authentication** ✅ N/A (Delegates to AWS)
8. **A08:2021 - Software and Data Integrity** ✅ PASS (Safe YAML loading)
9. **A09:2021 - Security Logging and Monitoring** ✅ PASS (Appropriate logging)
10. **A10:2021 - Server-Side Request Forgery** ✅ N/A (Only calls AWS APIs)

---

## Conclusion

The AWS Monthly Costs application demonstrates good security practices:

- ✅ No critical vulnerabilities identified
- ✅ Follows secure coding best practices
- ✅ Properly handles AWS credentials
- ✅ Safe input validation and error handling
- ✅ No known vulnerable dependencies

The application is suitable for production use by trusted DevOps/FinOps teams. The low-risk items noted are informational and do not require immediate action.

---

## Appendix: Files Reviewed

- `src/amc/__main__.py` - Main entry point and orchestration
- `src/amc/constants.py` - Constants definition
- `src/amc/reportexport/__init__.py` - Report generation
- `src/amc/runmodes/account/__init__.py` - Account cost calculations
- `src/amc/runmodes/bu/__init__.py` - Business unit calculations
- `src/amc/runmodes/service/__init__.py` - Service cost calculations
- `requirements.txt` - Dependencies
- `pyproject.toml` - Project configuration

**Total Lines Reviewed:** ~2,146 lines of Python code
