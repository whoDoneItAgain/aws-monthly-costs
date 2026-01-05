# Quick Start Guide - Automated Release Workflow

## Creating a New Release

### Step 1: Navigate to Actions
Go to your repository → Actions tab → Select "Automated Release" workflow

### Step 2: Run Workflow
Click "Run workflow" button and configure:

**Version Bump Type:**
- `auto` - Auto-detect from commits (recommended, default)
- `patch` - Bug fixes (e.g., 0.0.14 → 0.0.15)
- `minor` - New features (e.g., 0.0.14 → 0.1.0)
- `major` - Breaking changes (e.g., 0.0.14 → 1.0.0)
- Or specify exact version (e.g., `1.2.3`)

**Auto-Detection Keywords:**
- Major: `BREAKING CHANGE:`, `breaking:`, `major:`, `!:`
- Minor: `feat:`, `feature:`, `add:`, `new:`
- Patch: `fix:`, `bugfix:`, `patch:`, `repair:`

### Step 3: Monitor Progress
The workflow will:
1. ✅ Auto-detect or use selected version bump
2. ✅ Calculate new version number
3. ✅ Update `src/amc/version.py`
4. ✅ Generate changelog entry
5. ✅ Update `CHANGELOG.md`
6. ✅ Create a pull request for the release
7. ✅ PR runs through pr-ci.yml workflow (tests, lint, format)
8. ✅ Once PR is merged, create git tag
9. ✅ Create GitHub Release
10. ✅ Publish to PyPI

### Expected Results
- ✅ New version tag in repository
- ✅ GitHub Release with auto-generated notes
- ✅ Package published at https://pypi.org/p/aws-monthly-costs
- ✅ Updated CHANGELOG.md in repository

## Troubleshooting

### Release PR Fails CI Checks
- Review pr-ci.yml workflow logs for the release PR
- Fix failing tests or checks
- Push fixes to the release branch
- PR will automatically re-run CI checks
- Once checks pass, merge the PR to complete the release

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
