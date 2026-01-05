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
- Manual workflow re-runs or manual triggering is required

## Solutions

### Option 1: Use a Personal Access Token (PAT) - **Recommended**
Create a fine-grained Personal Access Token with appropriate permissions and use it instead of `GITHUB_TOKEN`:

1. Create a fine-grained PAT with these permissions:
   - Repository: Contents (read & write)
   - Repository: Pull requests (read & write)
   - Repository: Workflows (read & write)

2. Add the PAT as a repository secret (e.g., `PAT_TOKEN`)

3. Update `.github/workflows/release.yml`:
   ```yaml
   - name: Create Pull Request
     uses: peter-evans/create-pull-request@v7.0.0
     with:
       token: ${{ secrets.PAT_TOKEN }}  # Changed from GITHUB_TOKEN
   ```

### Option 2: Use a GitHub App Token
Create a GitHub App with appropriate permissions and use its token. This is more secure than a PAT for organization repositories.

### Option 3: Manual Workflow Trigger
Keep the current setup and manually trigger workflows for release PRs:
1. Navigate to the PR
2. Go to Actions tab
3. Manually trigger the "Pull Request CI" workflow

### Option 4: Workflow Call Pattern
Use `workflow_call` to trigger checks programmatically after PR creation:

```yaml
- name: Trigger PR Checks
  uses: peter-evans/repository-dispatch@v2
  with:
    token: ${{ secrets.GITHUB_TOKEN }}
    event-type: pr-checks
    client-payload: '{"pr": "${{ steps.create-pr.outputs.pull-request-number }}"}'
```

## Current Status
- The release workflow successfully creates PRs
- PRs are properly labeled and formatted
- CI checks must be manually triggered

## Recommendation
Implement **Option 1 (PAT)** as it's the simplest and most reliable solution that maintains full automation without requiring manual intervention.

## References
- [GitHub Actions: Using GITHUB_TOKEN](https://docs.github.com/en/actions/security-guides/automatic-token-authentication)
- [peter-evans/create-pull-request: Triggering workflows](https://github.com/peter-evans/create-pull-request#triggering-further-workflow-runs)
- [GitHub Actions: Events that trigger workflows](https://docs.github.com/en/actions/using-workflows/events-that-trigger-workflows#pull_request)
