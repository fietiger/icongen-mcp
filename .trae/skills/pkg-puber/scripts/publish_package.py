#!/usr/bin/env python3
"""
Automated Python package publishing script.
Publishes packages to PyPI or TestPyPI using twine.
"""

import subprocess
import sys
import os
from pathlib import Path


def get_api_token(repository: str = "pypi") -> str:
    """
    Get API token from environment variable or .env file.
    
    Args:
        repository: Repository name (pypi or testpypi)
    
    Returns:
        API token string or None
    """
    # Try environment variable first
    env_var = f"TEST_PYPI_API_TOKEN" if repository == "testpypi" else "PYPI_API_TOKEN"
    token = os.environ.get(env_var)
    
    if token:
        print(f"Using API token from {env_var}")
        return token
    
    # Try .env file
    env_file = Path.cwd() / ".env"
    if env_file.exists():
        try:
            with open(env_file, encoding='utf-8') as f:
                for line in f:
                    if line.startswith(env_var + "="):
                        token = line.strip().split("=", 1)[1]
                        print(f"Using API token from {env_var} in .env file")
                        return token
        except Exception as e:
            print(f"Warning: Failed to read .env file: {e}", file=sys.stderr)
    
    return None


def publish_package(
    package_path: str = "dist",
    repository: str = "pypi",
    skip_existing: bool = False,
    username: str = "__token__",
    password: str = None
) -> bool:
    """
    Publish Python package to PyPI or TestPyPI.
    
    Args:
        package_path: Path to the package file or directory (e.g., dist/)
        repository: Repository name (pypi or testpypi)
        skip_existing: Whether to skip existing versions
        username: Username (default: __token__)
        password: API token (if None, reads from environment or prompts)
    
    Returns:
        True if publish succeeded, False otherwise
    """
    package_path = Path(package_path).resolve()
    
    if not package_path.exists():
        print(f"Error: Package path does not exist: {package_path}")
        return False
    
    if package_path.is_dir():
        package_pattern = str(package_path / "*")
        print(f"Publishing packages in: {package_path}")
    else:
        package_pattern = str(package_path)
        print(f"Publishing package: {package_path}")
    
    # Build twine command
    cmd = [sys.executable, "-m", "twine", "upload", package_pattern]
    
    if repository == "testpypi":
        cmd.extend(["--repository", "testpypi"])
        print("Publishing to TestPyPI")
    else:
        print("Publishing to PyPI")
    
    if skip_existing:
        cmd.append("--skip-existing")
        print("Skipping existing versions")
    
    # Get password
    if not password:
        password = get_api_token(repository)
    
    if password:
        cmd.extend(["--username", username, "--password", password])
    else:
        print(f"No API token found, will prompt for credentials", file=sys.stderr)
    
    try:
        # Don't capture output to avoid encoding issues on Windows
        result = subprocess.run(cmd, check=True)
        
        print("\nPublish successful!")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"Publish failed with exit code {e.returncode}", file=sys.stderr)
        return False
    except FileNotFoundError:
        print("Error: 'twine' module not installed. Run: pip install twine", file=sys.stderr)
        return False


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Publish Python package")
    parser.add_argument(
        "package_path",
        nargs="?",
        default="dist",
        help="Path to package file or directory (default: dist/)"
    )
    parser.add_argument(
        "--repository",
        choices=["pypi", "testpypi"],
        default="pypi",
        help="Repository to publish to (default: pypi)"
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip existing versions"
    )
    parser.add_argument(
        "--password",
        help="API token (if not provided, reads from environment or prompts)"
    )
    
    args = parser.parse_args()
    
    success = publish_package(
        args.package_path,
        repository=args.repository,
        skip_existing=args.skip_existing,
        password=args.password
    )
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()