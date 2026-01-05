# Workflow Automation Issue: PR Checks Not Triggering

## Problem
Automated pull requests created by the release workflow (e.g., PR #128) do not automatically trigger the PR CI workflow checks.

## Root Cause
According to [GitHub Actions documentation](https://docs.github.com/en/actions/security-guides/automatic-token-authentication#using-the-github_token-in-a-workflow), when a workflow uses `GITHUB_TOKEN` to create a pull request, it intentionally **does not trigger other workflows**. This is a security feature to prevent recursive workflow executions.

From the peter-evans/create-pull-request action documentation:
> Pull requests created by the action using the default `GITHUB_TOKEN` cannot trigger other workflows.

## Impact
- Release PRs (like #128) are created successfully
- However, the required PR CI checks (tests, linting, formatting) don't automatically run  
- This blocks the PR from being merged due to branch protection rules

## Solution Implemented

### Automatic Workaround (Current Implementation)
The release workflow now includes an automatic workaround that:
1. **Tries to use PAT_TOKEN first** (if configured as a repository secret)
2. **Falls back to GITHUB_TOKEN** with an automatic trigger mechanism
3. **Closes and reopens the PR** to trigger the `reopened` event, which activates the PR CI workflow

This workaround ensures that PR checks are automatically triggered regardless of which token is used.

### How It Works
```yaml
# In release.yml
- Uses PAT_TOKEN if available, otherwise GITHUB_TOKEN
- After PR creation, runs a script that:
  1. Closes the newly created PR
  2. Waits 2 seconds  
  3. Reopens the PR
  4. The 'reopened' event triggers the PR CI workflow
```

### Optional: Configure PAT for Better Performance
While the workaround functions correctly, using a PAT provides a cleaner solution without the close/reopen dance:

1. Create a fine-grained PAT with these permissions:
   - Repository: Contents (read & write)
   - Repository: Pull requests (read & write)
   - Repository: Workflows (read & write)

2. Add the PAT as a repository secret named `PAT_TOKEN`

3. The workflow will automatically use it (no code changes needed)

## Current Status
✅ **Issue Resolved**: PRs created by the release workflow now automatically trigger CI checks through the close/reopen workaround

## Alternative Solutions (Not Needed)

### Option 1: GitHub App Token  
Create a GitHub App with appropriate permissions and use its token. More secure for organization repositories.

### Option 2: Manual Workflow Trigger
Keep using GITHUB_TOKEN without workaround and manually trigger workflows for each release PR.

## References
- [GitHub Actions: Using GITHUB_TOKEN](https://docs.github.com/en/actions/security-guides/automatic-token-authentication)
- [peter-evans/create-pull-request: Triggering workflows](https://github.com/peter-evans/create-pull-request#triggering-further-workflow-runs)
- [GitHub Actions: Events that trigger workflows](https://docs.github.com/en/actions/using-workflows/events-that-trigger-workflows#pull_request)
