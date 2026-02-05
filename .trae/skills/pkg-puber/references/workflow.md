# Workflow Documentation

Detailed workflows for Python package management.

## Complete Package Release Workflow

### Phase 1: Preparation

#### 1.1 Verify Project Structure

Ensure project has proper structure:

```
my-package/
├── src/
│   └── my_package/
│       ├── __init__.py
│       └── module.py
├── tests/
│   └── test_module.py
├── README.md
├── LICENSE
├── pyproject.toml
└── requirements.txt
```

#### 1.2 Update Version Number

Update version in `pyproject.toml`:

```toml
[project]
version = "1.0.0"  # Increment version
```

Follow semantic versioning:
- MAJOR: Incompatible API changes
- MINOR: Backwards-compatible functionality additions
- PATCH: Backwards-compatible bug fixes

#### 1.3 Update Changelog

Update `CHANGELOG.md`:

```markdown
## [1.0.0] - 2026-01-16

### Added
- Initial release
- Feature X
- Feature Y

### Fixed
- Bug fix Z
```

#### 1.4 Run Tests

Ensure all tests pass:

```bash
pytest tests/
```

### Phase 2: Build

#### 2.1 Clean Old Build Artifacts

```bash
rm -rf build dist *.egg-info
```

Or use provided script:

```bash
python scripts/build_package.py --no-clean
```

#### 2.2 Build Package

```bash
python -m build
```

Or use provided script:

```bash
python scripts/build_package.py
```

#### 2.3 Verify Build Output

Check `dist/` directory:

```bash
ls -lh dist/
```

Expected output:
- `package-name-version-py3-none-any.whl`
- `package-name-version.tar.gz`

### Phase 3: Validation

#### 3.1 Validate Package

```bash
python -m twine check dist/*
```

Or use provided script:

```bash
python scripts/validate_package.py
```

#### 3.2 Fix Validation Errors

Common issues and fixes:

**Missing long description:**
```toml
[project]
readme = "README.md"
```

**Invalid metadata:**
- Check TOML syntax
- Ensure all required fields are present
- Verify license format

**Missing license:**
```toml
[project]
license = {text = "MIT"}
```

### Phase 4: Testing

#### 4.1 Test Local Installation

```bash
pip install dist/package-name-version-py3-none-any.whl
```

#### 4.2 Verify Installation

```bash
python -c "import package_name; print(package_name.__version__)"
```

#### 4.3 Test Functionality

Run manual tests or automated tests:

```bash
pytest tests/
```

#### 4.4 Uninstall Test Package

```bash
pip uninstall package-name
```

### Phase 5: Publishing

#### 5.1 Setup API Token

Set environment variable:

```bash
export PYPI_API_TOKEN="pypi-..."
```

Or create `~/.pypirc`:

```ini
[pypi]
username = __token__
password = pypi-...
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
env_file = Path.cwd() / ".env"
token = None
if env_file.exists():
    with open(env_file, encoding='utf-8') as f:
        for line in f:
            if line.startswith("PYPI_API_TOKEN="):
                token = line.strip().split("=", 1)[1]
                break
```

#### 5.2 Publish to TestPyPI (Recommended)

```bash
python -m twine upload dist/* --repository testpypi
```

Or use provided script:

```bash
python scripts/publish_package.py --repository testpypi
```

#### 5.3 Test Installation from TestPyPI

```bash
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ package-name
```

#### 5.4 Verify TestPyPI Package

Visit: https://test.pypi.org/project/package-name/

#### 5.5 Publish to PyPI

```bash
python -m twine upload dist/*
```

Or use provided script:

```bash
python scripts/publish_package.py
```

#### 5.6 Verify PyPI Package

Visit: https://pypi.org/project/package-name/

### Phase 6: Post-Release

#### 6.1 Tag Release

```bash
git tag -a v1.0.0 -m "Release version 1.0.0"
git push origin v1.0.0
```

#### 6.2 Update Documentation

Update documentation with new features.

#### 6.3 Announce Release

Announce release to users:
- GitHub release
- Blog post
- Email announcement
- Social media

## Hotfix Workflow

### Scenario: Critical bug in production version

#### 1. Create Hotfix Branch

```bash
git checkout -b hotfix/v1.0.1
```

#### 2. Fix Bug

Make necessary code changes.

#### 3. Update Version

```toml
[project]
version = "1.0.1"
```

#### 4. Update Changelog

```markdown
## [1.0.1] - 2026-01-16

### Fixed
- Critical bug fix
```

#### 5. Build and Test

```bash
python -m build
python -m twine check dist/*
pip install dist/package-name-1.0.1-py3-none-any.whl
pytest tests/
```

#### 6. Publish Hotfix

```bash
python -m twine upload dist/*
```

#### 7. Merge Back

```bash
git checkout main
git merge hotfix/v1.0.1
git push origin main
```

## Feature Branch Workflow

### Scenario: New feature for next release

#### 1. Create Feature Branch

```bash
git checkout -b feature/new-feature
```

#### 2. Develop Feature

Implement new functionality.

#### 3. Write Tests

Add tests for new feature.

#### 4. Update Documentation

Document new feature.

#### 5. Update Changelog

```markdown
## [Unreleased]

### Added
- New feature description
```

#### 6. Build and Test

```bash
python -m build
python -m twine check dist/*
pip install dist/package-name-version-py3-none-any.whl
pytest tests/
```

#### 7. Merge to Main

```bash
git checkout main
git merge feature/new-feature
git push origin main
```

## Continuous Integration Workflow

### Automated Build and Test

#### GitHub Actions Example

```yaml
name: Build and Test

on: [push, pull_request]

jobs:
  build:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.8, 3.9, 3.10, 3.11]
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install build twine pytest
        pip install -e .
    
    - name: Run tests
      run: pytest tests/
    
    - name: Build package
      run: python -m build
    
    - name: Check package
      run: python -m twine check dist/*
```

### Automated Publish on Tag

```yaml
name: Publish to PyPI

on:
  push:
    tags:
      - 'v*'

jobs:
  publish:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install build twine
    
    - name: Build package
      run: python -m build
    
    - name: Publish to PyPI
      env:
        TWINE_USERNAME: __token__
        TWINE_PASSWORD: ${{ secrets.PYPI_API_TOKEN }}
      run: twine upload dist/*
```

## Troubleshooting Workflow

### Build Fails

#### 1. Check Dependencies

```bash
pip install -e .
```

#### 2. Check Build Output

```bash
python -m build --verbose
```

#### 3. Check Project Structure

Ensure all required files are present.

#### 4. Check Python Version

```bash
python --version
```

Ensure Python version matches classifiers in `pyproject.toml`.

### Validation Fails

#### 1. Check Metadata

```bash
python -m twine check dist/* --verbose
```

#### 2. Check README

Ensure README.md exists and is properly formatted.

#### 3. Check License

Ensure license is properly specified in `pyproject.toml`.

#### 4. Check Classifiers

Ensure classifiers are valid and match package metadata.

### Publish Fails

#### 1. Check API Token

```bash
echo $PYPI_API_TOKEN
```

Ensure token is set and valid.

#### 2. Check Network Connection

```bash
curl https://pypi.org
```

#### 3. Check Package Version

Ensure version doesn't already exist on PyPI.

#### 4. Check Package Size

Ensure package is under PyPI size limits (60MB).

#### 5. Check Repository URL

Ensure repository URL is correct:

```bash
python -m twine upload dist/* --verbose
```

## Windows-Specific Workflow

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

env_file = Path.cwd() / ".env"
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

## Best Practices

1. **Always test on TestPyPI first** before publishing to PyPI
2. **Version management**: Follow semantic versioning (MAJOR.MINOR.PATCH)
3. **Changelog**: Keep CHANGELOG.md up to date
4. **Testing**: Run tests before every release
5. **Validation**: Always run `twine check` before publishing
6. **Documentation**: Update README and documentation with each release
7. **Security**: Never commit API tokens to version control
8. **Backups**: Keep backup of old versions
9. **Communication**: Announce releases to users
10. **Monitoring**: Monitor package usage and issues after release