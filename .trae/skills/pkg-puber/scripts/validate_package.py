#!/usr/bin/env python3
"""
Automated Python package validation script.
Validates package compliance with PyPI standards using twine.
"""

import subprocess
import sys
from pathlib import Path


def validate_package(package_path: str) -> bool:
    """
    Validate a Python package using twine check.
    
    Args:
        package_path: Path to the package file or directory (e.g., dist/)
    
    Returns:
        True if validation passed, False otherwise
    """
    package_path = Path(package_path).resolve()
    
    if not package_path.exists():
        print(f"Error: Package path does not exist: {package_path}")
        return False
    
    if package_path.is_dir():
        package_pattern = str(package_path / "*")
        print(f"Validating all packages in: {package_path}")
    else:
        package_pattern = str(package_path)
        print(f"Validating package: {package_path}")
    
    try:
        result = subprocess.run(
            [sys.executable, "-m", "twine", "check", package_pattern],
            capture_output=True,
            text=True,
            check=True
        )
        
        print(result.stdout)
        
        if result.stderr:
            print("Warnings:", file=sys.stderr)
            print(result.stderr, file=sys.stderr)
        
        print("\nValidation passed!")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"Validation failed with exit code {e.returncode}", file=sys.stderr)
        print(e.stdout)
        print(e.stderr, file=sys.stderr)
        return False
    except FileNotFoundError:
        print("Error: 'twine' module not installed. Run: pip install twine", file=sys.stderr)
        return False


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Validate Python package")
    parser.add_argument(
        "package_path",
        nargs="?",
        default="dist",
        help="Path to the package file or directory (default: dist/)"
    )
    
    args = parser.parse_args()
    
    success = validate_package(args.package_path)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()