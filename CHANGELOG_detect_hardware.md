# Hardware Detector - Changelog

## Version 2.1.0 (2025-11-06)

### Breaking Changes
- **Python 3.9+ Required**: Dropped Python 2.7 compatibility
- Shebang changed from `python` to `python3`
- Removed `from __future__ import print_function`

### Version Management Improvements
- **Module-level version constants**: Added `__version__` and `__schema_version__` at top of file
- Version now displayed in: CLI help, `--version` flag, console report, and JSON output
- JSON output now includes both `version` (script) and `schema_version` (data format) fields
- New `--version` CLI flag: `detect_hardware_v2.py --version` shows version info

### Code Modernization
- **Type hints**: Added comprehensive type annotations throughout
  - Function parameters and return types
  - Class attributes and local variables
  - Using `Dict`, `List`, `Optional`, `Any`, `Tuple` from `typing`
- **F-strings**: Converted all `.format()` calls to f-strings for cleaner code
- **pathlib**: Replaced `os.path` operations with `pathlib.Path` objects
  - Path operations: `.exists()`, `.read_text()`, `.write_text()`, `.mkdir()`
  - Glob patterns: `.glob()`, `.rglob()`, `.iterdir()`
- **subprocess**: Updated to modern `subprocess.run()` with `capture_output=True, text=True`
- **datetime**: Using `datetime.utcnow().isoformat()` instead of `time.strftime()`

### Architecture Improvements
- **Refactored main()**: Moved argparse logic into dedicated `main()` function
- **Better error handling**: More descriptive error messages with modern string formatting
- **Cleaner imports**: All imports organized at top with type hints included

### CLI Enhancements
- Help text updated to show Python 3 commands
- Examples now use `python3` instead of `python`
- Version information integrated into argparse

### JSON Output Changes
- Added `version` field: Script version (e.g., "2.1.0")
- Renamed field: `timestamp` format unchanged but generated via `datetime.utcnow()`
- Field `system.uname` now serialized as dict (was tuple)

### Performance & Reliability
- More efficient file I/O with `Path.read_text()` / `Path.write_text()`
- Automatic parent directory creation in `to_json()`
- Better exception handling with explicit error messages

### Compatibility Notes
- **Not backward compatible** with Python 2.7
- Requires Python 3.9+ for type hint features
- JSON schema remains compatible (schema version 2.1 is extension of 2.0)
- All CLI flags remain unchanged for drop-in replacement

### Migration Guide
For systems running Python 2.7:
1. Upgrade to Python 3.9+ or keep using old version
2. Update shebang if using direct execution: `#!/usr/bin/env python3`
3. Update shell aliases/scripts: `python` → `python3`
4. JSON output structure unchanged, safe to parse with same code

---

## Version 2.0.0 (2025-10-24)

Initial release with:
- Multi-GPU support (NVIDIA, AMD, Intel)
- RAPL and AMD energy detection
- AMD uProf integration
- NUMA topology detection
- hwmon sensor detection
- lspci fallback for GPU detection
- CLI arguments: `--output-dir`, `--filename`, `--quiet`, `--json-only`
