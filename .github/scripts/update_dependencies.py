#!/usr/bin/env python3
"""Update Python dependencies in requirements.txt"""
import json
import subprocess
import sys

def main():
    with open('/tmp/outdated.json', 'r') as f:
        packages = json.load(f)
    
    for pkg in packages:
        print(f"Updating {pkg['name']} from {pkg['version']} to {pkg['latest_version']}")
        subprocess.run(['pip', 'install', '--upgrade', pkg['name']], check=False)

if __name__ == '__main__':
    main()
