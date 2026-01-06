---
name: UE5 Python API Validator
description: Validate UE5 Python scripts for correctness, check for deprecated APIs, and verify parameter constraints.
---

# UE5 Python API Validator

Use this skill to validate Unreal Engine Python scripts. It checks for:
- Existence of classes and methods
- Usage of deprecated APIs
- Parameter constraints (e.g. min/max values)
- Property access rights (read/write)

It automatically generates a mock `unreal` module from your project's Python stub file (`Intermediate/PythonStub/unreal.py`) to perform accurate validation.

## Usage

### 1. Validate a Script
To validate a specific script file:

```bash
python scripts/validate.py <path_to_script>
```

### 2. Check API Details
To look up details for a class or method:

```bash
python scripts/validate.py --query <ClassName.method_name>
```

## How It Works

- **Auto-Mock Generation**: The skill automatically converts the `unreal.py` stub file into a functional `mock_unreal` module located in `lib/mock_unreal`.
- **Runtime Validation**: Uses the generated mock module to simulate UE5 Python environment.
- **Metadata Analysis**: Uses C++ metadata (via `cpp_metadata_extractor.py`) for enhanced static analysis.
