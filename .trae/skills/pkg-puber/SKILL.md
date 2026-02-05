---
name: pkg-puber
description: Python package building, validation, and publishing automation. Use when Claude needs to build Python packages (.whl and .tar.gz), validate package compliance with PyPI standards, publish packages to PyPI or TestPyPI, or query package information from PyPI. This skill provides command-line workflows for package management tasks including building with python -m build, validation with twine check, and publishing with twine upload.
---

# Pkg Puber

## Overview

Automate Python package building, validation, and publishing workflows using standard command-line tools. This skill provides step-by-step procedures for creating distribution packages, verifying compliance, and publishing to package repositories.

## Quick Start

### Build a Python Package

```bash
cd /path/to/project
python -m build
```

This creates `dist/*.whl` and `dist/*.tar.gz` files.

### Validate Package

```bash
python -m twine check dist/*
```

### Publish to PyPI

```bash
python -m twine upload dist/* --username __token__ --password $PYPI_API_TOKEN
```

Or use interactive mode (prompts for credentials):

```bash
python -m twine upload dist/*
```

## Core Tasks

### Task 1: Build Package

Build Python distribution packages from a project with `pyproject.toml` or `setup.py`.

**Prerequisites:**
- Project has `pyproject.toml` or `setup.py`
- Build tools installed: `pip install build`

**Commands:**

```bash
# Build in current directory
python -m build

# Build in specific directory
cd /path/to/project && python -m build

# Clean build artifacts first
rm -rf build dist *.egg-info && python -m build
```

**Output:**
- `dist/package-name-version-py3-none-any.whl` (wheel)
- `dist/package-name-version.tar.gz` (source distribution)

**Common Issues:**
- Missing dependencies: Install with `pip install -e .`
- Invalid metadata: Check `pyproject.toml` or `setup.py`
- Build failures: Review error output for missing files or syntax errors

### Task 2: Validate Package

Verify package compliance with PyPI standards before publishing.

**Prerequisites:**
- Package built and available in `dist/`
- Twine installed: `pip install twine`

**Commands:**

```bash
# Check all packages in dist/
python -m twine check dist/*

# Check specific package
python -m twine check dist/package-1.0.0-py3-none-any.whl
```

**Validation Checks:**
- Metadata completeness
- Long description rendering
- File structure compliance
- License information

**Common Issues:**
- Missing long description: Add `readme` field in `pyproject.toml`
- Invalid metadata format: Check TOML syntax
- Missing license: Add `license` field

### Task 3: Publish Package

Upload packages to PyPI or TestPyPI repositories.

**Prerequisites:**
- Valid PyPI API token
- Package validated with `twine check`
- Twine installed: `pip install twine`

**Setup API Token:**

```bash
# Set environment variable
export PYPI_API_TOKEN="pypi-..."

# Or use TestPyPI
export TEST_PYPI_API_TOKEN="pypi-..."
```

**Using .env file (Recommended):**

Create `.env` file in project root:
```env
PYPI_API_TOKEN=pypi-...
TEST_PYPI_API_TOKEN=pypi-...
```

Read token in Python:
```python
from pathlib import Path
env_file = Path(__file__).parent / ".env"
token = None
if env_file.exists():
    with open(env_file, encoding='utf-8') as f:
        for line in f:
            if line.startswith("PYPI_API_TOKEN="):
                token = line.strip().split("=", 1)[1]
                break
```

**Commands:**

```bash
# Publish to PyPI with token
python -m twine upload dist/* --username __token__ --password $PYPI_API_TOKEN

# Publish to TestPyPI
python -m twine upload dist/* --username __token__ --password $TEST_PYPI_API_TOKEN --repository testpypi

# Interactive mode (prompts for credentials)
python -m twine upload dist/*

# Skip existing versions
python -m twine upload dist/* --skip-existing
```

**Repository URLs:**
- PyPI: `https://upload.pypi.org/legacy/`
- TestPyPI: `https://test.pypi.org/legacy/`

**Common Issues:**
- Authentication failed: Verify API token is valid
- Version exists: Use `--skip-existing` or bump version
- Invalid package: Run `twine check` first

### Task 4: Query Package Information

Retrieve package metadata from PyPI.

**Commands:**

```bash
# Using curl
curl https://pypi.org/pypi/package-name/json

# Using requests Python
python -c "import requests; print(requests.get('https://pypi.org/pypi/package-name/json').json())"
```

**Information Available:**
- Latest version
- All available versions
- Release dates
- Package metadata
- Download statistics

## Workflow: Complete Package Release

Follow this workflow for a complete package release:

1. **Prepare Project**
   ```bash
   cd /path/to/project
   # Ensure pyproject.toml is complete
   # Update version number
   ```

2. **Build Package**
   ```bash
   python -m build
   ```

3. **Validate Package**
   ```bash
   python -m twine check dist/*
   ```

4. **Test Installation (Optional)**
   ```bash
   pip install dist/package-name-version-py3-none-any.whl
   ```

5. **Publish to PyPI**
   ```bash
   python -m twine upload dist/* --username __token__ --password $PYPI_API_TOKEN
   ```

## Configuration

### pyproject.toml Template

See `assets/pyproject.toml` for a complete template.

### Required Fields

```toml
[project]
name = "package-name"
version = "1.0.0"
description = "Package description"
readme = "README.md"
license = {text = "MIT"}
authors = [
    {name = "Author Name", email = "author@example.com"},
]
dependencies = [
    "dependency>=1.0.0",
]
```

### Build System

```toml
[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"
```

## Resources

### scripts/

Executable scripts for automation tasks:

- `build_package.py` - Automated package building
- `validate_package.py` - Automated package validation
- `publish_package.py` - Automated package publishing

### references/

Documentation and reference materials:

- `commands.md` - Complete command reference
- `config.md` - Configuration file reference
- `workflow.md` - Detailed workflow documentation

### assets/

Template files:

- `pyproject.toml` - Complete pyproject.toml template

## Best Practices

1. **Always validate before publishing**: Run `twine check` before `twine upload`
2. **Use TestPyPI first**: Test on TestPyPI before publishing to PyPI
3. **Version management**: Follow semantic versioning (MAJOR.MINOR.PATCH)
4. **Changelog**: Maintain CHANGELOG.md for version history
5. **API tokens**: Store tokens in environment variables or .env file, not in code
6. **Clean builds**: Remove old build artifacts before new builds
7. **Test installation**: Install the built package locally to verify it works

## Windows-Specific Considerations

### PowerShell Encoding Issues

Windows PowerShell may encounter encoding issues with Unicode characters. To resolve:

**Option 1: Use .env file**
```env
PYPI_API_TOKEN=pypi-...
```

**Option 2: Set UTF-8 encoding in Python**
```python
import io
import sys

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
```

**Option 3: Use subprocess without capture**
```python
import subprocess
result = subprocess.run(cmd)  # Don't use capture_output=True
```

### PowerShell Command Limitations

Long commands in PowerShell may trigger PSReadLine errors. Use these workarounds:

**Option 1: Create Python script**
```python
# publish.py
import subprocess
import sys
from pathlib import Path

env_file = Path(__file__).parent / ".env"
token = None
if env_file.exists():
    with open(env_file, encoding='utf-8') as f:
        for line in f:
            if line.startswith("PYPI_API_TOKEN="):
                token = line.strip().split("=", 1)[1]
                break

cmd = [sys.executable, "-m", "twine", "upload", "dist/*",
          "--username", "__token__", "--password", token]
subprocess.run(cmd)
```

**Option 2: Use shorter commands**
```powershell
# Split into multiple commands
cd /path/to/project
python -m twine upload dist/* --username __token__ --password $env:PYPI_API_TOKEN
```

## Real-World Example

### Successful Publishing Workflow

Based on actual publishing experience:

1. **Project Structure**
   ```
   pkg_publisher_standalone/
   ├── src/
   │   └── pkg_publisher/
   ├── pyproject.toml
   ├── README.md
   ├── LICENSE
   └── .env
   ```

2. **Build**
   ```bash
   python -m build
   # Output: pkg_publisher-0.1.0-py3-none-any.whl (22.6 kB)
   # Output: pkg_publisher-0.1.0.tar.gz (22.8 kB)
   ```

3. **Validate**
   ```bash
   python -m twine check dist/*
   # Output: PASSED for both files
   ```

4. **Publish**
   ```bash
   # Using Python script to avoid PowerShell issues
   python publish_pkg.py
   # Output: Successfully uploaded to PyPI
   ```

5. **Verify**
   Visit: https://pypi.org/project/pkg-publisher/

### Common Pitfalls and Solutions

**Pitfall 1: PowerShell encoding errors**
- **Problem**: `UnicodeEncodeError: 'gbk' codec can't encode character`
- **Solution**: Use .env file or Python script instead of inline commands

**Pitfall 2: PSReadLine buffer errors**
- **Problem**: `System.ArgumentOutOfRangeException` in PowerShell
- **Solution**: Use Python scripts or split commands into smaller parts

**Pitfall 3: Token not found**
- **Problem**: `PYPI_API_TOKEN not found in environment variables`
- **Solution**: Create .env file or set environment variable explicitly

**Pitfall 4: Package validation fails**
- **Problem**: `twine check` returns errors
- **Solution**: Check pyproject.toml for required fields (name, version, description, readme, license)