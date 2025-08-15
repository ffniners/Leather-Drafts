# patternlab (starter)

Python-based engine for drafting leather patterns using a small DSL → SVG/DXF,
with reproducible, per-project runs.

## Why Python?
- Excellent geometry & CAD ecosystem (Shapely, pyclipper, ezdxf, pythonOCC)
- Easy to glue JSON/YAML schemas, CLIs, and CI
- Fast iteration; later you can offload heavy nesting to a Node worker if needed

## Repo layout
```
patternlab/
  engine/            # reusable engine (never copy per project)
  blocks/            # versioned canonical base blocks
  recipes/           # style/panelization masters
  schemas/           # JSON Schemas for validation
  tests/             # unit + golden tests
  projects/          # per-client runs (inputs + outputs)
  .github/workflows/ # CI
```
See inline comments in the engine and CLI for how to extend.

## Quick start
```bash
# (Optional) create venv
python -m venv .venv && source .venv/bin/activate

# install
pip install -e .

# smoke test
pl --help

# draft → construct → package (starter no-op pipeline)
pl draft --recipe recipes/jacket_princess_v2.yml          --measurements projects/example/measurements.json          --out projects/example/tmp/base.json

pl construct --in projects/example/tmp/base.json              --options projects/example/options.yml              --out projects/example/tmp/constructed.json

pl package --in projects/example/tmp/constructed.json            --out projects/example/outputs/
```

## Notes
- This starter keeps geometry simple so it installs everywhere.
- For precise curve offsets (seam allowances without faceting), integrate `pythonocc-core` later.
- For advanced nesting, consider wiring a Node worker that calls SVGNest; keep packaging here simple.


## DXF export (AC1018)
After `construct`, export DXF for CAD/CAM:

```bash
pl export-dxf --in projects/example/tmp/constructed.json               --out projects/example/outputs/pattern_AC1018.dxf               --units mm               --splines off               --flatten-tol 0.2               --arcs segment
```
Notes:
- Sets `$INSUNITS=4` when `--units mm`.
- `--splines on` uses DXF SPLINE (some CAMs prefer polylines; default is off).
- `--flatten-tol` controls curve faceting when not using splines.
