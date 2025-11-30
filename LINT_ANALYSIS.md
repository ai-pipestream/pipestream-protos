# Protobuf Lint Error Analysis

**Total errors: 346**

## Error Categories

### 1. Package/Directory Structure (100 errors) - **BREAKING IF FIXED**
- **48 errors**: Files not in directory matching package name
  - Example: `ai.pipestream.config.v1` files in `core/` instead of `ai/pipestream/config/v1/`
- **33 errors**: Multiple packages in same directory
  - Example: `core/` contains files from `ai.pipestream.config.v1`, `ai.pipestream.data.v1`, etc.
- **19 errors**: Package missing version suffix
  - Example: `ai.pipestream.events` should be `ai.pipestream.events.v1`

**Impact**: Would require massive file reorganization and break all existing imports
**Recommendation**: **DISABLE** these rules in buf.yaml (already partially disabled)

---

### 2. Enum Naming (66 errors) - **BREAKING IF FIXED**
- Enum values missing proper prefix
  - Example: `DELETE`, `ADD`, `UPDATE` should be `INTENT_DELETE`, `INTENT_ADD`, `INTENT_UPDATE`
- Enum zero values missing `_UNSPECIFIED` suffix
  - Example: `DELETE` (zero value) should be `INTENT_DELETE_UNSPECIFIED`

**Impact**: Would break all existing code using these enums
**Recommendation**: **DECIDE** - Either disable or fix systematically as a breaking change

---

### 3. RPC Naming (97 errors) - **BREAKING IF FIXED**
- RPC request/response types don't follow standard naming conventions
  - Example: `GetHealth(HealthRequest) returns (HealthResponse)` should use `GetHealthRequest` / `GetHealthResponse`
- Some RPCs not PascalCase
  - Example: `streamDocuments` should be `StreamDocuments`

**Impact**: Would break all client/server code
**Recommendation**: **DECIDE** - Either disable or fix systematically as a breaking change

---

### 4. Shared Request/Response Types (64 errors) - **NON-BREAKING WARNING**
- Same message type used for multiple RPCs
  - Example: `ProcessNodeRequest` used by both `ProcessNode` and `ProcessStream` RPCs

**Impact**: Not a breaking change, just a warning about potential confusion
**Recommendation**: **DISABLE** - This is a style preference, not a correctness issue

---

### 5. Service Suffix (5 errors) - **BREAKING IF FIXED**
- Services don't end with "Service"
  - Example: `PipeStepProcessor` should be `PipeStepProcessorService`

**Impact**: Would break service discovery and client code
**Recommendation**: **DECIDE** - Either disable or fix systematically

---

### 6. Java Options Inconsistency (4 errors) - **NON-BREAKING**
- Some files in same package have `java_package` / `java_multiple_files` options, others don't

**Impact**: Non-breaking - just needs consistency
**Recommendation**: **FIX** - Easy to add missing options

---

### 7. Field/Oneof Naming (3 errors) - **BREAKING IF FIXED**
- Fields using camelCase instead of snake_case
  - Example: `blobBag` should be `blob_bag`
  - Example: `blobData` (oneof) should be `blob_data`

**Impact**: Would break all code accessing these fields
**Recommendation**: **DECIDE** - Small number, could fix manually

---

### 8. Unused Imports (3 errors) - **NON-BREAKING**
- Import statements that aren't used

**Impact**: None - purely cosmetic
**Recommendation**: **FIX** - Very easy, just remove the imports

---

## Recommended Action Plan

### Phase 1: Non-Breaking Fixes (LOW EFFORT, NO RISK)
1. ✅ **Remove unused imports** (3 files)
2. ✅ **Add missing Java options for consistency** (2 files)

**Effort**: 15 minutes
**Risk**: None

---

### Phase 2: Buf Configuration (MEDIUM EFFORT, NO RISK)
Update `buf.yaml` to explicitly disable rules we won't enforce:

```yaml
lint:
  use:
    - STANDARD
  except:
    # Directory structure - too disruptive to fix
    - PACKAGE_DIRECTORY_MATCH
    - PACKAGE_VERSION_SUFFIX
    - PACKAGE_SAME_DIRECTORY

    # Naming - breaking changes
    - ENUM_VALUE_PREFIX
    - ENUM_ZERO_VALUE_SUFFIX
    - FIELD_LOWER_SNAKE_CASE
    - ONEOF_LOWER_SNAKE_CASE
    - RPC_REQUEST_STANDARD_NAME
    - RPC_RESPONSE_STANDARD_NAME
    - SERVICE_SUFFIX

    # Warnings only - not errors
    - RPC_REQUEST_RESPONSE_UNIQUE
    - FILE_OPTION_EQUAL_JAVA_PACKAGE
```

**Effort**: 5 minutes
**Risk**: None (explicitly documents what we're not enforcing)

---

### Phase 3: Breaking Changes (IF DESIRED)
If you want to enforce strict standards, these would need to be done in a major version:

1. **Enum naming** (66 errors)
   - Write a script to add prefixes and `_UNSPECIFIED` suffixes
   - Regenerate all code
   - Update all uses

2. **RPC naming** (97 errors)
   - Rename all request/response types
   - Regenerate all code
   - Update all client/server implementations

3. **Field naming** (3 errors)
   - Manual fix - only 3 fields affected

4. **Service suffix** (5 errors)
   - Add "Service" to 5 service names
   - Update service registration

**Effort**: Multiple days
**Risk**: High - breaks all existing code

---

## Summary Statistics

| Category | Count | Breaking? | Recommendation |
|----------|-------|-----------|----------------|
| Package structure | 100 | ✅ Yes | Disable in buf.yaml |
| Enum naming | 66 | ✅ Yes | Disable (or major version fix) |
| RPC naming | 97 | ✅ Yes | Disable (or major version fix) |
| Shared types | 64 | ❌ No | Disable (style only) |
| Service suffix | 5 | ✅ Yes | Disable (or major version fix) |
| Java options | 4 | ❌ No | Fix (easy) |
| Field naming | 3 | ✅ Yes | Disable (or fix manually) |
| Unused imports | 3 | ❌ No | Fix (easy) |
| **TOTAL** | **346** | | |
| **Non-breaking fixes** | **7** | ❌ No | **DO THESE** |
| **Breaking changes** | **339** | ✅ Yes | **DISABLE OR DEFER** |

---

## Proposed Immediate Actions

### Option A: Minimal (Recommended)
1. Fix 7 non-breaking errors (imports + Java options)
2. Update buf.yaml to disable all breaking rules
3. **Result**: 0 errors, ~30 minutes of work

### Option B: Partial Enforcement
1. Fix 7 non-breaking errors
2. Fix 3 field naming errors manually
3. Fix 5 service suffix errors
4. Update buf.yaml to disable remaining rules
5. **Result**: 0 errors, ~2 hours of work, limited breaking changes

### Option C: Full Compliance (Major Version)
1. Fix ALL 346 errors
2. Regenerate all stubs
3. Update all services and clients
4. Coordinate breaking change across all teams
5. **Result**: 0 errors, multiple days of work, massive breaking changes

---

## Next Steps

Please review this analysis and decide:
1. Which option (A, B, or C) should we pursue?
2. Are there specific error categories you want to handle differently?
3. Should we prioritize any particular area?
