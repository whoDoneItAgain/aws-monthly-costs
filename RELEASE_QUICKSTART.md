# Quick Start Guide - Automated Release Workflow

## Creating a New Release

### Step 1: Navigate to Actions
Go to your repository → Actions tab → Select "Automated Release" workflow

### Step 2: Run Workflow
Click "Run workflow" button and configure:

**Version Bump Type:**
- `patch` - Bug fixes (e.g., 0.0.14 → 0.0.15)
- `minor` - New features (e.g., 0.0.14 → 0.1.0)
- `major` - Breaking changes (e.g., 0.0.14 → 1.0.0)
- Or specify exact version (e.g., `1.2.3`)

### Step 3: Monitor Progress
The workflow will:
1. ✅ Calculate new version number
2. ✅ Update `src/amc/version.py`
3. ✅ Generate changelog entry
4. ✅ Update `CHANGELOG.md`
5. ✅ Run tests (fails if tests fail)
6. ✅ Create git tag
7. ✅ Create GitHub Release
8. ✅ Publish to PyPI

### Expected Results
- ✅ New version tag in repository
- ✅ GitHub Release with auto-generated notes
- ✅ Package published at https://pypi.org/p/aws-monthly-costs
- ✅ Updated CHANGELOG.md in repository

## Managing Dependencies

### Via Dependabot (Recommended)
Dependabot runs weekly and creates PRs for outdated dependencies:
1. Review the Dependabot PR
2. Tests run automatically via pr-ci workflow
3. Merge the PR if tests pass
4. Create a release with updated dependencies

### Manual Updates
Update dependencies manually before creating a release:

```bash
# Check for outdated dependencies
pip list --outdated

# Update specific packages
pip install --upgrade boto3 pyyaml openpyxl

# Update requirements.txt
pip freeze | grep -E "^(boto3|pyyaml|openpyxl)==" > requirements.txt

# Commit and push (tests will run via pr-ci on the PR)
git checkout -b update-deps
git add requirements.txt
git commit -m "chore: update dependencies"
git push origin update-deps
# Create PR and merge after tests pass
```

## Troubleshooting

### Workflow Fails During Tests
- Review test logs in the workflow run
- Fix failing tests
- Push fixes to main
- Re-run the workflow

### Version Already Exists
- Choose a different version number
- Or delete the existing tag/release (not recommended)

### PyPI Publishing Fails
- Ensure PyPI project is configured for trusted publishing
- Verify the `pypi` environment exists in repository settings
- Check that the version number is unique

## Manual Release (Not Recommended)

If automated workflow fails, you can release manually:

```bash
# Update version
echo '__version__ = "X.Y.Z"' > src/amc/version.py

# Update CHANGELOG.md manually

# Commit and tag
git add src/amc/version.py CHANGELOG.md
git commit -m "chore: bump version to X.Y.Z"
git tag -a vX.Y.Z -m "Release vX.Y.Z"
git push origin main --tags
```

Then create a GitHub Release manually, which triggers PyPI publishing.

## Files Modified by Workflows

**Automated Release Workflow:**
- `src/amc/version.py` - Version number
- `CHANGELOG.md` - Changelog entries and links

## Best Practices

1. **Ensure all PRs are merged** before creating a release (pr-ci workflow tests all PRs)
2. **Update dependencies** before major/minor releases
3. **Use patch releases** for bug fixes only
4. **Review the generated CHANGELOG.md** after release
5. **Monitor the workflow run** to ensure all steps complete successfully

## Getting Help

- Full documentation: [RELEASE_WORKFLOW.md](RELEASE_WORKFLOW.md)
- Issues with workflows: Check GitHub Actions logs
- Questions: Open an issue in the repository
