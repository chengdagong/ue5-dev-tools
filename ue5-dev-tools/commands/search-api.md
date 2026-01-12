---
description: Search UE5 Python API definitions
---

# /search-api

Search UE5 Python API definitions using fuzzy or exact matching.

## Usage

```
/search-api <query> [filters]
```

### Query Types

| Type | Example | Description |
|------|---------|-------------|
| Fuzzy search | `/search-api actor` | Word-boundary matching in names and signatures |
| Chained search | `/search-api actor render` | Multiple terms filter progressively |
| Exact class | `/search-api unreal.Actor` | Full class definition |
| Exact member | `/search-api unreal.Actor.on_destroyed` | Specific member definition |
| Wildcard | `/search-api unreal.Actor.*location*` | Pattern matching within a class |
| Multiple queries | `/search-api unreal.Actor\|Pawn\|log` | Pipe-separated queries |

### Filters (fuzzy search only)

| Filter | Description |
|--------|-------------|
| `-c` | Classes only |
| `-m` | Methods only |
| `-e` | Enum values only |

## Steps

Run the API search script:

```bash
python ${CLAUDE_PLUGIN_ROOT}/skills/ue5-api-expert/scripts/api-search.py $ARGUMENTS
```

Display the script's output directly without interpretation.

## Examples

```
/search-api inputmapping
/search-api unreal.EnhancedInputComponent
/search-api unreal.Actor.*location*
/search-api -m get_actor
```
