# Version Management Standards

## Version Number Format
- Use 3 dotted digit version numbers: `MAJOR.MINOR.PATCH`
- Example: `1.2.15`

## Version Increment Rules

### MAJOR Version (First Digit)
- Increment when making incompatible API changes
- Increment when adding major new features that change the core functionality
- **When incremented**: update dist directory and create zip distribution file (do not update GitHub unless told to
- **Reset**: MINOR and PATCH to 0

### MINOR Version (Second Digit)  
- Increment when adding functionality in a backwards compatible manner
- Increment when adding new features or significant enhancements
- **When incremented**: update dist directory and create zip distribution file (do not update GitHub unless told to)
- **Reset**: PATCH to 0

### PATCH Version (Third Digit)
- **CRITICAL**: Increment for EVERY successful build
- Increment for backwards compatible bug fixes
- Increment for small improvements and patches
- **When incremented**: No GitHub update required (unless told to update GitHub)

## Build Process Requirements

### Automatic Version Increment
1. **Before every build**: Increment PATCH version automatically
2. **After successful build**: Version file should reflect new PATCH number
3. **Build artifacts**: Should include the incremented version number

### Manual Version Updates
- MAJOR/MINOR versions should be updated manually when appropriate
- Use version management scripts to update version numbers
# - Always commit version changes to source control

## Implementation Requirements

### Version File Structure
```python
# In project/version.py
__version__ = "1.0.15"  # MAJOR.MINOR.PATCH format
__author__ = "Mark Oldham"
__compile_date__ = "2026-01-01"
```

### Build Scripts
- `increment_build.py`: Must increment PATCH version before build
- `update_version.py`: For manual MAJOR/MINOR version updates
- Version increment must be atomic and fail-safe

### Distribution Requirements
- Executable filename must not include version: `project.exe`
- ZIP distribution must include version: `project_v1.0.15.zip`
- All build artifacts must reflect current version

## GitHub Integration

### Repository Updates
- Push to GitHub only when told to.
- Tag releases with version numbers: `v1.0.15`
- Include version information in release notes
- Include pushing zip file to releases when updating GitHub

### Version History
- Maintain CHANGELOG.md with version history
- Document what changed in each version
- Link versions to GitHub releases

## Enforcement

### Build Validation
- Build process MUST fail if version increment fails
- Version number MUST be validated before creating distributions
- No duplicate version numbers allowed

### Quality Gates
- Version increment is mandatory for all builds
- Version format must be validated (3 dotted digits)
- Build artifacts must include correct version information

## Examples

### Successful Build Sequence
```
Before build: 1.0.14
After build:  1.0.15
Next build:   1.0.16
```

### Feature Addition
```
Before: 1.0.15
After:  1.1.0  (MINOR increment, PATCH reset)
```

### Major Release
```
Before: 1.5.23
After:  2.0.0  (MAJOR increment, MINOR/PATCH reset)
```

## Error Handling

### Build Failures
- If build fails, do NOT increment version
- Version should only increment on successful completion
- Failed builds should not affect version numbering

### Version Conflicts
- Detect and prevent duplicate version numbers
- Validate version format before increment
- Provide clear error messages for version issues

This document ensures consistent version management across all projects and eliminates confusion about when and how to increment version numbers.