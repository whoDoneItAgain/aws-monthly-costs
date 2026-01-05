# Release and Publishing Workflows

This document describes the automated release and publishing workflows for the aws-monthly-costs project.

## Overview

The project includes automated workflows to manage releases and PyPI publishing:

1. **Automated Release** (`release.yml`) - Main workflow for creating releases
2. **PyPI Publishing** (`pypi.yaml`) - Publishes to PyPI when a release is created

## Semantic Versioning

This project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html):

- **MAJOR** version (X.0.0): Incompatible API changes
- **MINOR** version (0.X.0): New functionality in a backward compatible manner
- **PATCH** version (0.0.X): Backward compatible bug fixes

## Creating a Release

### Prerequisites

Before creating a release:
1. Ensure all PRs are merged to main branch (tests will have run via pr-ci workflow)
2. Review the current version number

### Automated Release Workflow

The primary way to create a release is through the **Automated Release** workflow:

1. Go to **Actions** → **Automated Release** in the GitHub repository
2. Click **Run workflow**
3. Select the branch (usually `main`)
4. Choose the version bump type:
   - `auto` - Automatically detects based on commit messages (default)
   - `patch` - For bug fixes (0.0.X)
   - `minor` - For new features (0.X.0)
   - `major` - For breaking changes (X.0.0)
   - Or specify an exact version like `1.2.3`
5. Click **Run workflow**

#### Auto-Detection Logic

When `auto` is selected, the workflow analyzes commit messages since the last release:

- **Major bump** if commits contain:
  - `BREAKING CHANGE:`
  - `breaking:`
  - `major:`
  - `!:` (indicating breaking change)

- **Minor bump** if commits contain:
  - `feat:`
  - `feature:`
  - `add:`
  - `new:`

- **Patch bump** if commits contain:
  - `fix:`
  - `bugfix:`
  - `patch:`
  - `repair:`

If no keywords are detected, defaults to `patch`.

**Note:** You can always override auto-detection by manually selecting a specific bump type.

### What the Automated Release Workflow Does

The workflow performs the following steps automatically:

#### 1. Version Bump
- Reads the current version from `src/amc/version.py`
- Auto-detects or uses manual selection for version bump
- Calculates the new version based on semantic versioning rules
- Updates the version file

#### 2. Changelog Generation
- Extracts commits since the last release
- Generates a changelog entry in `CHANGELOG.md`
- Follows the [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) format

#### 3. Pull Request Creation
- Creates a pull request with the version and changelog updates
- The PR will automatically run through the PR CI workflow which includes comprehensive testing
- Once the PR passes all required checks and is merged, the release is created automatically

#### 4. Release Creation
- Creates a git tag with the new version
- Creates a GitHub Release with auto-generated notes
- Includes the changelog entry in release notes

#### 5. PyPI Publishing
- Builds the Python package
- Publishes to PyPI using trusted publishing
- Package becomes available at https://pypi.org/p/aws-monthly-costs

## PyPI Publishing

The PyPI publishing workflow (`pypi.yaml`) is automatically triggered when a GitHub Release is published. It:

1. Checks out the release tag
2. Sets up Python
3. Installs build dependencies
4. Builds the package (wheel and source distribution)
5. Publishes to PyPI using trusted publishing (no API tokens needed)

### Prerequisites for PyPI Publishing

The PyPI publishing uses **Trusted Publishers**, which requires:
- The repository must be configured in PyPI project settings
- The workflow must run from the main branch or a release tag
- The GitHub Actions environment `pypi` must exist
- A `PAT_TOKEN` secret must be configured in repository settings for the release workflow to trigger the PyPI workflow (alternatively, the workflow falls back to `GITHUB_TOKEN` but this prevents automatic PyPI workflow triggering)

## Changelog Management

The `CHANGELOG.md` file follows the [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) format:

### Structure
```markdown
## [Unreleased]
### Added
### Changed
### Deprecated
### Removed
### Fixed
### Security

## [Version] - YYYY-MM-DD
### Category
- Change description
```

### Categories
- **Added**: New features
- **Changed**: Changes in existing functionality
- **Deprecated**: Soon-to-be removed features
- **Removed**: Removed features
- **Fixed**: Bug fixes
- **Security**: Security fixes

The changelog is automatically updated during the release process, but can be manually edited to provide more context.

## Workflow Triggers

### Automated Release
- **Manual**: `workflow_dispatch` with version bump input
- **When to use**: Ready to create a new release after updating dependencies and ensuring tests pass

### PyPI Publishing
- **Automatic**: Triggered when a GitHub Release is published
- **When to use**: Never manually triggered (runs automatically)

## Best Practices

1. **Before Creating a Release**:
   - Ensure all PRs are merged to main
   - Review the current version number
   - Decide on the appropriate version bump
   - Note: All code has already been tested via the required PR CI workflow before merge

2. **Version Bumping Guidelines**:
   - Use `patch` for bug fixes and minor updates
   - Use `minor` for new features that don't break existing functionality
   - Use `major` for breaking changes
   - Use specific version only when necessary (e.g., aligning with another project)

3. **Changelog Maintenance**:
   - Review auto-generated changelog entries
   - Add manual entries for significant changes
   - Keep the Unreleased section up to date

## Troubleshooting

### Release Workflow Fails
- Check the workflow logs in the Actions tab
- Ensure all tests pass
- Verify the version number is valid
- Check that there are no merge conflicts

### PyPI Publishing Fails
- Verify the PyPI project is configured for trusted publishing
- Check that the version number is unique (not already published)
- Ensure the `pypi` environment exists in repository settings

### PyPI Publishing Doesn't Trigger After Release
- Ensure a `PAT_TOKEN` (Personal Access Token) secret is configured in repository settings
- The PAT must have `repo` scope to trigger workflows
- If `PAT_TOKEN` is not available, workflows created by `GITHUB_TOKEN` won't trigger other workflows (GitHub security feature)
- To verify: Check the Actions tab for pypi workflow runs after release creation

### Release PR Fails CI Checks
- Review the PR CI workflow logs for the release PR
- Fix any failing tests or checks locally
- Push fixes to the release branch
- The PR will automatically re-run CI checks

## Manual Release Process

If you need to create a release manually (not recommended):

```bash
# Update version
echo '__version__ = "X.Y.Z"' > src/amc/version.py

# Update changelog
# Edit CHANGELOG.md manually

# Commit changes
git add src/amc/version.py CHANGELOG.md
git commit -m "chore: bump version to X.Y.Z"

# Create tag
git tag -a vX.Y.Z -m "Release vX.Y.Z"

# Push
git push origin main --tags
```

Then create a GitHub Release manually, which will trigger the PyPI publishing workflow.

   - Review the current version number
   - Decide on the appropriate version bump

2. **Version Bumping Guidelines**:
   - Use `patch` for bug fixes and minor updates
   - Use `minor` for new features that don't break existing functionality
   - Use `major` for breaking changes
   - Use specific version only when necessary (e.g., aligning with another project)

3. **Dependency Updates**:
   - Review Dependabot PRs regularly
   - Test dependency updates before merging
   - Consider bundling multiple dependency updates in a release

4. **Changelog Maintenance**:
   - Review auto-generated changelog entries
   - Add manual entries for significant changes
   - Keep the Unreleased section up to date

## Troubleshooting

### Release Workflow Fails
- Check the workflow logs in the Actions tab
- Ensure all tests pass
- Verify the version number is valid
- Check that there are no merge conflicts

### PyPI Publishing Fails
- Verify the PyPI project is configured for trusted publishing
- Check that the version number is unique (not already published)
- Ensure the `pypi` environment exists in repository settings

### Dependency Updates Fail
- Check for breaking changes in dependency changelogs
- Run tests with updated dependencies
- Consider pinning problematic dependencies temporarily

## Manual Release Process

If you need to create a release manually (not recommended):

```bash
# Update version
echo '__version__ = "X.Y.Z"' > src/amc/version.py

# Update changelog
# Edit CHANGELOG.md manually

# Commit changes
git add src/amc/version.py CHANGELOG.md
git commit -m "chore: bump version to X.Y.Z"

# Create tag
git tag -a vX.Y.Z -m "Release vX.Y.Z"

# Push
git push origin main --tags
```

Then create a GitHub Release manually, which will trigger the PyPI publishing workflow.
