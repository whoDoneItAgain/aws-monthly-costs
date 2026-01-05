#!/usr/bin/env python3
"""Update Python dependencies in requirements.txt"""
import json
import subprocess
import sys

def main():
    try:
        with open('/tmp/outdated.json', 'r') as f:
            packages = json.load(f)
        
        failed = []
        for pkg in packages:
            print(f"Updating {pkg['name']} from {pkg['version']} to {pkg['latest_version']}")
            result = subprocess.run(
                ['pip', 'install', '--upgrade', pkg['name']], 
                capture_output=True, 
                text=True
            )
            if result.returncode != 0:
                print(f"Warning: Failed to update {pkg['name']}: {result.stderr}")
                failed.append(pkg['name'])
        
        if failed:
            print(f"\nWarning: The following packages failed to update: {', '.join(failed)}")
            print("Continuing with successful updates...")
            
    except Exception as e:
        print(f"Error updating dependencies: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()
