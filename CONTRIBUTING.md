# Contributing

Thanks for helping improve `cursor-fleet`.

## Development

```bash
python3 -m pip install -e .
python3 -m compileall src scripts tests
python3 -m unittest discover -s tests
```

## Design principles

1. Codex should see one task and one final result.
2. Backend workers should receive narrow prompts and bounded path ownership.
3. Write-heavy work must go through isolated Git worktrees.
4. The final patch is applied only after integration and verification, unless explicitly overridden.
5. No secrets should be passed to Cursor prompts or logs.

## Pull requests

Please include:

- What changed.
- How you tested it.
- Any safety or compatibility implications.
