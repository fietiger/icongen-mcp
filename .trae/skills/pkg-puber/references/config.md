# Configuration Reference

Reference for Python package configuration files.

## pyproject.toml

### Basic Structure

```toml
[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

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

### Required Fields

#### name
Package name (must be unique on PyPI).

```toml
name = "my-package"
```

**Rules:**
- Lowercase letters, numbers, underscores, hyphens
- Must start with letter or underscore
- 1-64 characters

#### version
Package version following semantic versioning.

```toml
version = "1.0.0"
```

**Format:** MAJOR.MINOR.PATCH

#### description
Short package description.

```toml
description = "A brief description of the package"
```

**Rules:**
- One line
- Maximum 200 characters

#### readme
Path to README file.

```toml
readme = "README.md"
```

**Supported formats:** .md, .rst, .txt

#### license
Package license.

```toml
license = {text = "MIT"}
```

**Common licenses:** MIT, Apache-2.0, GPL-3.0, BSD-3-Clause

#### authors
Package authors.

```toml
authors = [
    {name = "Author Name", email = "author@example.com"},
]
```

### Optional Fields

#### classifiers
PyPI classifiers for package categorization.

```toml
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.8",
    "Programming Language :: Python :: 3.9",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
]
```

**Common classifiers:**
- Development Status: 1-Planning, 2-Pre-Alpha, 3-Alpha, 4-Beta, 5-Production/Stable
- Intended Audience: Developers, End Users/Desktop, System Administrators
- License: OSI Approved :: MIT License, etc.
- Programming Language: Python :: 3, Python :: 3.8, etc.
- Topic: Software Development, System, etc.

#### keywords
Package keywords for search.

```toml
keywords = ["keyword1", "keyword2", "keyword3"]
```

#### urls
Project URLs.

```toml
[project.urls]
Homepage = "https://github.com/username/package-name"
Repository = "https://github.com/username/package-name"
Documentation = "https://package-name.readthedocs.io"
"Bug Tracker" = "https://github.com/username/package-name/issues"
```

#### dependencies
Package dependencies.

```toml
dependencies = [
    "requests>=2.31.0",
    "numpy>=1.24.0",
    "pandas>=2.0.0",
]
```

**Version specifiers:**
- `>=1.0.0`: Minimum version
- `==1.0.0`: Exact version
- `~=1.0.0`: Compatible release (>=1.0.0, <2.0.0)
- `>=1.0.0,<2.0.0`: Version range

#### optional-dependencies
Optional dependency groups.

```toml
[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "black>=23.0.0",
    "flake8>=6.0.0",
]
docs = [
    "sphinx>=7.0.0",
    "sphinx-rtd-theme>=1.3.0",
]
```

**Usage:**
```bash
pip install package-name[dev]
pip install package-name[dev,docs]
```

#### scripts
Command-line scripts.

```toml
[project.scripts]
my-command = "my_package.module:function"
```

#### entry-points
Entry points for plugins.

```toml
[project.entry-points."my_plugin_group"]
my_plugin = "my_package.plugin:PluginClass"
```

### Build System Configuration

#### requires
Build dependencies.

```toml
[build-system]
requires = ["setuptools>=61.0", "wheel", "build>=0.10.0"]
```

#### build-backend
Build backend to use.

```toml
[build-system]
build-backend = "setuptools.build_meta"
```

**Options:**
- `setuptools.build_meta`: setuptools backend
- `flit_core.buildapi`: Flit backend
- `poetry.core.masonry.api`: Poetry backend

### Tool Configuration

#### setuptools

```toml
[tool.setuptools.packages.find]
where = ["src"]
include = ["my_package*"]

[tool.setuptools.dynamic]
dependencies = {file = ["requirements.txt"]}
```

#### black

```toml
[tool.black]
line-length = 88
target-version = ['py38', 'py39', 'py310', 'py311']
include = '\.pyi?$'
extend-exclude = '''
/(
  # directories
  \.eggs
  | \.git
  | \.hg
  | \.mypy_cache
  | \.tox
  | \.venv
  | build
  | dist
)/
'''
```

#### flake8

```toml
[tool.flake8]
max-line-length = 88
extend-ignore = ["E203", "W503"]
exclude = [
    ".git",
    "__pycache__",
    "build",
    "dist",
]
```

#### pytest

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
```

#### mypy

```toml
[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
```

## setup.py (Legacy)

Legacy setup.py configuration (use pyproject.toml instead).

```python
from setuptools import setup, find_packages

setup(
    name="my-package",
    version="1.0.0",
    description="Package description",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="Author Name",
    author_email="author@example.com",
    url="https://github.com/username/package-name",
    packages=find_packages(),
    install_requires=[
        "requests>=2.31.0",
    ],
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
    ],
    python_requires=">=3.8",
)
```

## MANIFEST.in

Additional files to include in distribution.

```txt
include README.md
include LICENSE
include requirements.txt
recursive-include my_package/templates *.html
recursive-include my_package/static *.css *.js
global-exclude *.pyc
global-exclude __pycache__
```

## .pypirc

PyPI configuration file (located at ~/.pypirc).

```ini
[distutils]
index-servers =
    pypi
    testpypi

[pypi]
repository = https://upload.pypi.org/legacy/
username = __token__
password = pypi-...

[testpypi]
repository = https://test.pypi.org/legacy/
username = __token__
password = pypi-...
```

## Requirements Files

### requirements.txt

Runtime dependencies.

```txt
requests>=2.31.0
numpy>=1.24.0
pandas>=2.0.0
```

### requirements-dev.txt

Development dependencies.

```txt
-r requirements.txt
pytest>=7.0.0
black>=23.0.0
flake8>=6.0.0
mypy>=1.0.0
```

### requirements-test.txt

Test dependencies.

```txt
-r requirements.txt
pytest>=7.0.0
pytest-cov>=4.0.0
pytest-mock>=3.10.0
```

## Configuration Best Practices

1. **Use pyproject.toml** for new projects
2. **Specify exact versions** for dependencies in requirements files
3. **Use semantic versioning** for package versions
4. **Include classifiers** for better PyPI discoverability
5. **Add URLs** for homepage, repository, documentation
6. **Separate dev dependencies** using optional-dependencies
7. **Use tool configuration** for consistent formatting and linting
8. **Include license** and ensure it's compatible with dependencies
9. **Test installation** before publishing
10. **Validate configuration** using `twine check`