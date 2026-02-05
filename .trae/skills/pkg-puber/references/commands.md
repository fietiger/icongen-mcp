# Command Reference

Complete reference for Python package management commands.

## Build Commands

### python -m build

Build Python distribution packages.

**Usage:**
```bash
python -m build [options]
```

**Options:**
- `--outdir DIR`: Output directory for built packages (default: dist/)
- `--skip-dependency-check`: Skip checking for missing dependencies
- `--wheel`: Only build wheel
- `--sdist`: Only build source distribution
- `-n, --no-isolation`: Build in the current environment

**Examples:**
```bash
# Build in current directory
python -m build

# Build with custom output directory
python -m build --outdir ./packages

# Build only wheel
python -m build --wheel

# Build without isolation
python -m build -n
```

## Validation Commands

### python -m twine check

Validate package compliance with PyPI standards.

**Usage:**
```bash
python -m twine check [options] <package_files>
```

**Options:**
- `--strict`: Fail on warnings

**Examples:**
```bash
# Check all packages in dist/
python -m twine check dist/*

# Check specific package
python -m twine check dist/package-1.0.0-py3-none-any.whl

# Check with strict mode
python -m twine check --strict dist/*
```

## Publishing Commands

### python -m twine upload

Upload packages to PyPI or other repositories.

**Usage:**
```bash
python -m twine upload [options] <package_files>
```

**Options:**
- `--repository URL`: Repository URL
- `--repository-url URL`: Alias for --repository
- `--username USERNAME`: Username (default: __token__)
- `--password PASSWORD`: Password or API token
- `--sign`: Sign the package with GPG
- `--identity ID`: GPG identity to use
- `--skip-existing`: Skip files that already exist
- `--comment COMMENT`: Comment to upload
- `--verbose`: Show more output

**Examples:**
```bash
# Upload to PyPI with token
python -m twine upload dist/* --username __token__ --password $PYPI_API_TOKEN

# Upload to TestPyPI
python -m twine upload dist/* --repository testpypi --username __token__ --password $TEST_PYPI_API_TOKEN

# Upload with custom repository
python -m twine upload dist/* --repository https://upload.pypi.org/legacy/

# Skip existing versions
python -m twine upload dist/* --skip-existing

# Upload with verbose output
python -m twine upload dist/* --verbose
```

## Query Commands

### PyPI JSON API

Query package information from PyPI.

**Usage:**
```bash
curl https://pypi.org/pypi/<package_name>/json
```

**Examples:**
```bash
# Get package information
curl https://pypi.org/pypi/requests/json

# Get specific version
curl https://pypi.org/pypi/requests/2.31.0/json

# Get latest version
curl https://pypi.org/pypi/requests/json | jq '.info.version'
```

### pip search (deprecated)

Note: `pip search` is deprecated. Use PyPI web interface or API instead.

## Utility Commands

### pip install

Install packages from local files or PyPI.

**Examples:**
```bash
# Install from local wheel
pip install dist/package-1.0.0-py3-none-any.whl

# Install from local tar.gz
pip install dist/package-1.0.0.tar.gz

# Install in development mode
pip install -e .

# Install with dependencies
pip install -r requirements.txt
```

### pip show

Show package information.

**Examples:**
```bash
# Show package details
pip show package-name

# Show package location
pip show package-name | grep Location
```

### pip list

List installed packages.

**Examples:**
```bash
# List all packages
pip list

# List outdated packages
pip list --outdated

# List packages in specific format
pip list --format=json
```

## Environment Variables

### PYPI_API_TOKEN

PyPI API token for authentication.

```bash
export PYPI_API_TOKEN="pypi-..."
```

### TEST_PYPI_API_TOKEN

TestPyPI API token for authentication.

```bash
export TEST_PYPI_API_TOKEN="pypi-..."
```

### TWINE_REPOSITORY

Default repository URL for twine.

```bash
export TWINE_REPOSITORY="https://upload.pypi.org/legacy/"
```

### TWINE_USERNAME

Default username for twine.

```bash
export TWINE_USERNAME="__token__"
```

### TWINE_PASSWORD

Default password for twine.

```bash
export TWINE_PASSWORD="pypi-..."
```

## Repository URLs

### PyPI
- Upload: `https://upload.pypi.org/legacy/`
- API: `https://pypi.org/pypi/`

### TestPyPI
- Upload: `https://test.pypi.org/legacy/`
- API: `https://test.pypi.org/pypi/`

### Private Repositories
- DevPI: `https://devpi.example.com/`
- Artifactory: `https://artifactory.example.com/artifactory/api/pypi/pypi-local/`
- Nexus: `https://nexus.example.com/repository/pypi-hosted/`