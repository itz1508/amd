# Edge Rewrite

Automated gap evaluation and migration pipeline.

## Repository root

`D:\Dev\amd`

## Architecture authority

See [Source_Of_Truth.md](Source_Of_Truth.md) for the current AMD Track 1 runtime contract and validation rules.

## Setup

```powershell
cd D:\Dev\amd
uv sync
```

## Usage

```powershell
uv run amd_backend --help
```

## Development

Foundation files define structure and routing only. Phase behavior is implemented during migration tasks.
