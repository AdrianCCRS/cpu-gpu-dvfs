# Version Management - Proyecto 10

## Overview

This document describes the versioning strategy for the hardware detection scripts and related tools in Proyecto 10.

## Versioning System

### Two-Level Version Tracking

We use a **dual versioning system** to separate code changes from data format changes:

1. **Script Version** (`__version__`): Semantic versioning for code changes
2. **Schema Version** (`__schema_version__`): Data format compatibility version

### Script Version (`__version__`)

Format: **MAJOR.MINOR.PATCH** (Semantic Versioning 2.0.0)

- **MAJOR**: Breaking changes to Python API or CLI interface
  - Example: Dropping Python 2.7 support (1.x → 2.0)
  - Example: Removing CLI flags or changing their behavior
  
- **MINOR**: New features, backward compatible
  - Example: Adding new hardware detection (CPU→GPU support)
  - Example: Adding new CLI flags
  - Example: New fields in JSON output (backward compatible)
  
- **PATCH**: Bug fixes, no API changes
  - Example: Fixing GPU detection bug
  - Example: Correcting energy calculation
  - Example: Improving error messages

**Current Version**: `2.1.0`

### Schema Version (`__schema_version__`)

Format: **MAJOR.MINOR**

- **MAJOR**: Breaking changes to JSON structure
  - Example: Renaming fields
  - Example: Changing data types (string → dict)
  - Example: Removing fields
  
- **MINOR**: Backward compatible additions
  - Example: Adding new optional fields
  - Example: Adding new capabilities
  - Example: Additional metadata

**Current Schema**: `2.1`

## Implementation

### Code Location

```python
# At top of detect_hardware_v2.py (after docstring)
__version__ = "2.1.0"
__schema_version__ = "2.1"
```

### JSON Output

Every JSON report includes version information:

```json
{
  "version": "2.1.0",
  "schema_version": "2.1",
  "timestamp": "2025-11-06T21:03:32.916666Z",
  ...
}
```

### CLI Access

```bash
# Show version
python3 detect_hardware_v2.py --version
# Output: detect_hardware_v2.py 2.1.0 (schema 2.1)

# Version in help text
python3 detect_hardware_v2.py --help
# Shows: "Hardware Detector v2.1.0 - ..."

# Version in console report
python3 detect_hardware_v2.py
# Shows: "--- Proyecto10 Hardware Detection v2.1.0 (schema 2.1) ---"
```

## Version History

### 2.1.0 (2025-11-06) - Python 3.9+ Migration
- **Schema**: 2.0 → 2.1
- **Changes**:
  - Dropped Python 2.7 support
  - Added type hints throughout
  - Modern f-strings and pathlib
  - Added `version` field to JSON output
  - `system.uname` now dict (was tuple)

### 2.0.0 (2025-10-24) - Multi-GPU Support
- **Schema**: 1.0 → 2.0
- **Changes**:
  - Added multi-GPU detection
  - AMD uProf integration
  - NUMA topology
  - hwmon sensors
  - lspci GPU fallback

## Best Practices

### When to Bump Versions

#### Script Version

1. **MAJOR (2.x → 3.0)**:
   - Python version requirement change
   - Removing deprecated CLI flags
   - API breaking changes

2. **MINOR (2.1 → 2.2)**:
   - New detection features
   - New CLI options
   - Performance improvements
   - New optional JSON fields

3. **PATCH (2.1.0 → 2.1.1)**:
   - Bug fixes
   - Documentation updates
   - Error message improvements

#### Schema Version

1. **MAJOR (2.x → 3.0)**:
   - Incompatible JSON structure changes
   - Field renames or removals
   - Type changes

2. **MINOR (2.1 → 2.2)**:
   - New optional fields
   - Additional metadata
   - Extended capabilities

### Compatibility Checking

Downstream tools should check schema version for compatibility:

```python
import json

with open('hardware_report.json') as f:
    data = json.load(f)
    
schema = float(data.get('schema_version', '1.0'))

if schema < 2.0:
    print("Warning: Old schema detected")
elif schema >= 3.0:
    print("Error: Incompatible schema version")
```

### Release Process

1. **Update version constants** in code
2. **Document changes** in CHANGELOG_detect_hardware.md
3. **Test compatibility** with existing tools
4. **Update examples** in README/docs if needed
5. **Tag release** in git: `git tag v2.1.0`

## Rationale

### Why Two Version Numbers?

**Problem**: Code changes don't always mean data format changes.

**Solution**: Separate versioning allows:
- Bug fixes without worrying about data compatibility
- Data format stability across multiple code versions
- Clear communication to downstream tools about compatibility

### Why Module-Level Constants?

**Advantages**:
- Single source of truth
- Easy to access programmatically
- Consistent across CLI, JSON, and reports
- Can import into other modules: `from detect_hardware_v2 import __version__`

**Example**:
```python
from detect_hardware_v2 import __version__, __schema_version__

print(f"Using Hardware Detector v{__version__}")
print(f"Data format: schema {__schema_version__}")
```

## Future Considerations

### Version 3.0 Planning

Potential breaking changes for next major version:
- Restructure JSON for better ML feature extraction
- Split detection into modular plugins
- Add streaming/incremental detection mode
- Consider protobuf/msgpack for binary format

### Schema Evolution

Maintain backward compatibility by:
- Only adding optional fields in minor versions
- Using schema version checks in parsing code
- Providing migration scripts for major changes
- Documenting all field changes in changelog

---

**Last Updated**: 2025-11-06
**Current Versions**: Script 2.1.0, Schema 2.1
