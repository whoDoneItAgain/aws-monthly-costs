#!/usr/bin/env python3
"""Create dependency summary for GitHub Actions"""
import json

def main():
    with open('/tmp/outdated.json', 'r') as f:
        outdated = json.load(f)
    
    print("| Package | Current Version | Latest Version |")
    print("|---------|----------------|----------------|")
    
    for pkg in outdated:
        print(f"| {pkg['name']} | {pkg['version']} | {pkg['latest_version']} |")

if __name__ == '__main__':
    main()
