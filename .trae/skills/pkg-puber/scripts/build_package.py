#!/usr/bin/env python3
"""
Automated Python package building script.
Builds distribution packages (.whl and .tar.gz) from a Python project.
"""

import subprocess
import sys
import os
import shutil
from pathlib import Path


def clean_build_artifacts(project_path: str = ".") -> None:
    """
    Clean build artifacts from the project directory.
    
    Args:
        project_path: Path to the project directory
    """
    artifacts = ["build", "dist", "*.egg-info"]
    
    for artifact in artifacts:
        artifact_path = Path(project_path) / artifact
        if artifact_path.exists():
            if artifact_path.is_dir():
                shutil.rmtree(artifact_path)
                print(f"Removed directory: {artifact_path}")
            else:
                artifact_path.unlink()
                print(f"Removed file: {artifact_path}")


def build_package(project_path: str = ".", clean: bool = True) -> bool:
    """
    Build Python distribution packages.
    
    Args:
        project_path: Path to the project directory
        clean: Whether to clean build artifacts before building
    
    Returns:
        True if build succeeded, False otherwise
    """
    project_path = Path(project_path).resolve()
    
    if not project_path.exists():
        print(f"Error: Project path does not exist: {project_path}")
        return False
    
    if clean:
        print("Cleaning build artifacts...")
        clean_build_artifacts(str(project_path))
    
    print(f"Building package in: {project_path}")
    
    try:
        result = subprocess.run(
            [sys.executable, "-m", "build"],
            cwd=str(project_path),
            capture_output=True,
            text=True,
            check=True
        )
        
        print(result.stdout)
        
        if result.stderr:
            print("Warnings/Errors:", file=sys.stderr)
            print(result.stderr, file=sys.stderr)
        
        dist_path = project_path / "dist"
        if dist_path.exists():
            packages = list(dist_path.glob("*"))
            print(f"\nBuild successful! Created {len(packages)} package(s):")
            for pkg in packages:
                print(f"  - {pkg.name}")
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"Build failed with exit code {e.returncode}", file=sys.stderr)
        print(e.stdout)
        print(e.stderr, file=sys.stderr)
        return False
    except FileNotFoundError:
        print("Error: 'build' module not installed. Run: pip install build", file=sys.stderr)
        return False


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Build Python package")
    parser.add_argument(
        "project_path",
        nargs="?",
        default=".",
        help="Path to the project directory (default: current directory)"
    )
    parser.add_argument(
        "--no-clean",
        action="store_true",
        help="Do not clean build artifacts before building"
    )
    
    args = parser.parse_args()
    
    success = build_package(args.project_path, clean=not args.no_clean)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()