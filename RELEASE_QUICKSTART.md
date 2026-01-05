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
2. **Use patch releases** for bug fixes only
3. **Review the generated CHANGELOG.md** after release
4. **Monitor the workflow run** to ensure all steps complete successfully

## Getting Help

- Full documentation: [RELEASE_WORKFLOW.md](RELEASE_WORKFLOW.md)
- Issues with workflows: Check GitHub Actions logs
- Questions: Open an issue in the repository
