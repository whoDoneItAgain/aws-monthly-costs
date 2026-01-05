# GitHub Actions Workflow Migration Guide

## Summary of Changes

This PR consolidates the GitHub Actions workflows to follow a cleaner pattern with a single required check for branch protection.

### What Changed

1. **New: `pr-ci.yml`** - Consolidated PR CI workflow
   - Runs all PR checks: tests, linting, formatting, and label requirements
   - Includes a summary job (`All Tests Passed`) that aggregates all checks
   - Auto-cancels outdated runs when new commits are pushed
   - Provides nice summaries in the GitHub Actions UI
   - Supports manual triggering via workflow_dispatch

2. **Removed: `test.yaml`** - No longer needed
   - All testing now happens in `pr-ci.yml` before merge
   - With proper branch protection, main branch is always tested via PR checks
   - Manual testing can be done via workflow_dispatch on `pr-ci.yml`

3. **Removed: `pr-require-label.yaml`** - Functionality moved to `pr-ci.yml`
   - Label requirement is now part of the consolidated PR CI workflow

4. **Unchanged:** Other workflows remain as-is
   - `maintenance-pre-commit.yaml` - Still runs on schedule
   - `maintenance-label-sync.yaml` - Still syncs labels
   - `pypi.yaml` - Still publishes to PyPI on release

## How to Update Branch Protection

After this PR is merged, update your branch protection rules:

1. Go to **Settings** → **Branches** → **Branch protection rules** for `main`
2. Under **"Require status checks to pass before merging"**:
   - ✅ Add: `All Tests Passed`
   - ❌ Remove old checks: `Run Tests`, `Lint Code`, `require-pr-label`, etc.

### Why This is Better

- **Single Required Check**: Only need to require "All Tests Passed" in branch protection
- **Better CI Time**: Automatically cancels outdated runs when you push new commits
- **Cleaner UI**: All PR checks are grouped in one workflow
- **Better Visibility**: GitHub Actions summaries show status at a glance

## What Runs When

| Event | Workflows |
|-------|-----------|
| Pull Request | `pr-ci.yml` (all CI checks) |
| Manual Trigger | `pr-ci.yml` (via workflow_dispatch) |
| Schedule (every 2 hours) | `maintenance-pre-commit.yaml` |
| Push to main (if labels.yml changes) | `maintenance-label-sync.yaml` |
| Release published | `pypi.yaml` |

## Jobs in pr-ci.yml

1. **PR Information** - Displays PR details in summary
2. **Require Label** - Ensures PR has appropriate label
3. **Test** - Runs tests across Python 3.10-3.14 (matrix)
4. **Lint** - Runs code linting
5. **Format** - Checks code formatting
6. **All Tests Passed** - Summary job (⭐ this is the one to require)

The `All Tests Passed` job only succeeds if all other jobs pass, making it perfect for branch protection.
