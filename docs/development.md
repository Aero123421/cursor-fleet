# Development

```bash
python3 -m pip install -e .
python3 -m compileall src scripts tests
python3 -m unittest discover -s tests
```

## Running against a throwaway repo

```bash
mkdir /tmp/fleet-demo && cd /tmp/fleet-demo
git init
printf 'print("hello")\n' > app.py
git add app.py && git commit -m init
python3 /path/to/cursor-fleet/scripts/install_project.py --target .
python3 .codex/tools/cursor_fleet.py run --dry-run --mode implement --task "Add a README."
```

Remove run data:

```bash
python3 .codex/tools/cursor_fleet.py clean
```
