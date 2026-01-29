#!/usr/bin/env python3
"""
Validation script for Multi-Agent Router integration.

Run this script to verify the integration is properly installed and configured.

Usage:
    python3 validate.py
"""
import json
import os
import sys
from pathlib import Path


def check_file(filepath: str, description: str) -> bool:
    """Check if a file exists."""
    if Path(filepath).exists():
        print(f"✓ {description}: {filepath}")
        return True
    else:
        print(f"✗ {description}: {filepath} - MISSING")
        return False


def check_python_syntax(filepath: str) -> bool:
    """Check if Python file has valid syntax."""
    try:
        with open(filepath, 'r') as f:
            compile(f.read(), filepath, 'exec')
        print(f"  ✓ Syntax valid: {filepath}")
        return True
    except SyntaxError as e:
        print(f"  ✗ Syntax error in {filepath}: {e}")
        return False


def check_json(filepath: str) -> bool:
    """Check if JSON file is valid."""
    try:
        with open(filepath, 'r') as f:
            json.load(f)
        print(f"  ✓ Valid JSON: {filepath}")
        return True
    except json.JSONDecodeError as e:
        print(f"  ✗ JSON error in {filepath}: {e}")
        return False


def main():
    """Run validation checks."""
    print("Multi-Agent Router - Installation Validation")
    print("=" * 50)
    print()

    script_dir = Path(__file__).parent
    os.chdir(script_dir)

    all_passed = True

    # Check required files
    print("Checking required files...")
    required_files = [
        ("__init__.py", "Main module"),
        ("conversation_agent.py", "Conversation agent"),
        ("config_flow.py", "Config flow"),
        ("const.py", "Constants"),
        ("manifest.json", "Manifest"),
        ("strings.json", "UI strings"),
    ]

    for filepath, description in required_files:
        if not check_file(filepath, description):
            all_passed = False

    print()

    # Check Python syntax
    print("Checking Python syntax...")
    python_files = [
        "__init__.py",
        "conversation_agent.py",
        "config_flow.py",
        "const.py",
    ]

    for filepath in python_files:
        if Path(filepath).exists():
            if not check_python_syntax(filepath):
                all_passed = False

    print()

    # Check JSON validity
    print("Checking JSON files...")
    json_files = ["manifest.json", "strings.json"]

    for filepath in json_files:
        if Path(filepath).exists():
            if not check_json(filepath):
                all_passed = False

    print()

    # Check manifest content
    print("Checking manifest content...")
    try:
        with open("manifest.json", 'r') as f:
            manifest = json.load(f)

        checks = [
            ("domain", "multi_agent_router"),
            ("name", "Multi-Agent Router"),
            ("config_flow", True),
        ]

        for key, expected in checks:
            if key in manifest and manifest[key] == expected:
                print(f"  ✓ manifest.{key} = {expected}")
            else:
                print(f"  ✗ manifest.{key} should be {expected}")
                all_passed = False

        # Check that conversation is NOT in dependencies (to avoid timing issues)
        if "dependencies" not in manifest or "conversation" not in manifest.get("dependencies", []):
            print(f"  ✓ manifest.dependencies does not include 'conversation' (correct)")
        else:
            print(f"  ✗ manifest.dependencies should NOT include 'conversation' (causes timing issues)")
            all_passed = False

    except Exception as e:
        print(f"  ✗ Error checking manifest: {e}")
        all_passed = False

    print()

    # Check documentation
    print("Checking documentation...")
    doc_files = [
        "README.md",
        "INSTALL.md",
        "TESTING.md",
        "QUICKSTART.md",
    ]

    for filepath in doc_files:
        if Path(filepath).exists():
            print(f"  ✓ {filepath}")
        else:
            print(f"  ⚠ {filepath} - optional but recommended")

    print()

    # Check examples
    print("Checking examples...")
    example_files = [
        "examples/README.md",
        "examples/custom_sentences.yaml",
        "examples/intent_script.yaml",
    ]

    for filepath in example_files:
        if Path(filepath).exists():
            print(f"  ✓ {filepath}")
        else:
            print(f"  ⚠ {filepath} - optional")

    print()
    print("=" * 50)

    if all_passed:
        print("✓ All validation checks PASSED")
        print()
        print("The integration appears to be correctly installed.")
        print("Next steps:")
        print("  1. Restart Home Assistant")
        print("  2. Go to Settings → Devices & Services")
        print("  3. Click '+ Add Integration'")
        print("  4. Search for 'Multi-Agent Router'")
        print()
        print("For detailed setup instructions, see QUICKSTART.md")
        return 0
    else:
        print("✗ Some validation checks FAILED")
        print()
        print("Please fix the issues listed above and run this script again.")
        print("For help, see INSTALL.md or TESTING.md")
        return 1


if __name__ == "__main__":
    sys.exit(main())
