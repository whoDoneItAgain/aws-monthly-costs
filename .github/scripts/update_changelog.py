#!/usr/bin/env python3
"""Update CHANGELOG.md with new version"""
import os
import re
import subprocess
import sys

def get_repo_url():
    """Get GitHub repository URL from git remote"""
    try:
        result = subprocess.run(
            ['git', 'remote', 'get-url', 'origin'],
            capture_output=True,
            text=True,
            check=True
        )
        url = result.stdout.strip()
        # Convert SSH URL to HTTPS if needed
        if url.startswith('git@github.com:'):
            url = url.replace('git@github.com:', 'https://github.com/')
        # Remove .git suffix if present
        url = url.rstrip('.git')
        return url
    except subprocess.CalledProcessError:
        # Fallback to environment variable or hardcoded value
        return os.environ.get('GITHUB_SERVER_URL', 'https://github.com') + '/' + \
               os.environ.get('GITHUB_REPOSITORY', 'whoDoneItAgain/aws-monthly-costs')

def main():
    if len(sys.argv) != 3:
        print("Usage: update_changelog.py <new_version> <old_version>")
        sys.exit(1)
    
    new_version = sys.argv[1]
    old_version = sys.argv[2]
    repo_url = get_repo_url()
    
    with open('CHANGELOG.md', 'r') as f:
        content = f.read()
    
    # Read the changelog entry
    with open('/tmp/changelog_entry.md', 'r') as f:
        new_entry = f.read().strip()
    
    # Insert new entry after Unreleased section
    pattern = r'(## \[Unreleased\][^\n]*\n)'
    if re.search(pattern, content):
        content = re.sub(pattern, f'\\1\n{new_entry}\n\n', content, count=1)
    
    # Update version links at the bottom
    link_pattern = r'\n\[Unreleased\]:.*(\n\[[\d\.]+\]:.*)*'
    content = re.sub(link_pattern, '', content)
    
    # Add updated links
    new_links = f"""
[Unreleased]: {repo_url}/compare/v{new_version}...HEAD
[{new_version}]: {repo_url}/compare/v{old_version}...v{new_version}
[{old_version}]: {repo_url}/releases/tag/v{old_version}
"""
    
    content = content.rstrip() + '\n' + new_links
    
    with open('CHANGELOG.md', 'w') as f:
        f.write(content)
    
    print(f"Updated CHANGELOG.md with version {new_version}")

if __name__ == '__main__':
    main()
