import json
from pathlib import Path
from typing import Optional, List, Dict, Any

import typer

# Engine imports
from ..dsl.dsl_parser import parse_dsl, Piece, PathCmd  # demo DSL
from ..dsl.to_svg import pieces_to_svg                   # SVG preview
from ..geometry.eval import eval_expr                    # safe expression evaluator
from ..transforms.seam_allowance import offset_piece     # SA offset
# DXF exporter is imported inside the command to avoid hard dependency at import-time

app = typer.Typer(help="Leather Drafts CLI")


# ---------------------------
# Helpers
# ---------------------------

def _piece_to_json(piece: Piece) -> Dict[str, Any]:
    """Convert a Piece dataclass (with PathCmds) to a plain JSON-able dict."""
    return {
        "name": piece.name,
        "paths": [{"type": c.type, "data": c.data} for c in piece.paths],
        "notches": [[x, y, lbl] for (x, y, lbl) in getattr(piece, "notches", [])],
        "drills": [[x, y, lbl] for (x, y, lbl) in getattr(piece, "drills", [])],
        "grain": getattr(piece, "grain", None),
    }


def _coerce_expr(expr: str, env: Dict[str, Any]) -> float:
    """
    Evaluate an expression string possibly wrapped with {...}.
    Supports names like M.chest, F.ease_chest, O.hem_allowance and derived params.
    """
    s = expr.strip()
    if s.startswith("{") and s.endswith("}"):
        s = s[1:-1]
    return float(eval_expr(s, env))


# ---------------------------
# Commands
# ---------------------------

@app.command()
def draft(
    recipe: Path = typer.Option(..., exists=True, help="Recipe YAML (used for defaults/metadata)"),
    measurements: Path = typer.Option(..., exists=True, help="Measurements JSON (must include body/fit)"),
    out: Path = typer.Option(..., help="Output base JSON"),
    block: Optional[Path] = typer.Option(
        None, exists=True, help="Optional parametric block JSON; if provided, draft from block"
    ),
):
    """
    Draft base geometry.

    - If --block is provided, compute geometry from the parametric block JSON using the
      measurements (M), fit (F), and some basic options (O).
    - Otherwise, emit a small demo piece via the DSL to verify the pipeline.
    """
    out.parent.mkdir(parents=True, exist_ok=True)

    if block:
        import yaml

        # Load inputs
        meas = json.loads(Path(measurements).read_text())
        M = meas.get("body", {})
        F = meas.get("fit", {})
        try:
            R = yaml.safe_load(Path(recipe).read_text()) or {}
        except Exception:
            R = {}

        # Basic options (extend as needed / pull defaults from recipe if present)
        O = {"hem_allowance": R.get("defaults", {}).get("hem_allowance", 20)}

        block_data = json.loads(Path(block).read_text())
        env: Dict[str, Any] = {"M": M, "F": F, "O": O}

        # Compute derived top-level params into env (e.g., W, L, AD, ...)
        for k, ex in (block_data.get("params") or {}).items():
            env[k] = _coerce_expr(ex, env)

        pieces_out: List[Dict[str, Any]] = []
        for p in block_data.get("pieces", []):
            # piece-local params
            penv = dict(env)
            for k, ex in (p.get("params") or {}).items():
                penv[k] = _coerce_expr(ex, penv)

            # paths
            paths: List[Dict[str, Any]] = []
            for cmd in p.get("paths", []):
                t = cmd["type"]
                if t in ("MOVE", "LINE"):
                    x = _coerce_expr(cmd["expr"][0], penv)
                    y = _coerce_expr(cmd["expr"][1], penv)
                    paths.append({"type": t, "data": {"to": [round(x, 3), round(y, 3)]}})
                elif t == "CURVE":
                    cp1 = cmd["expr"]["cp1"]
                    cp2 = cmd["expr"]["cp2"]
                    to = cmd["expr"]["to"]
                    paths.append(
                        {
                            "type": "CURVE",
                            "data": {
                                "cp1": [round(_coerce_expr(cp1[0], penv), 3), round(_coerce_expr(cp1[1], penv), 3)],
                                "cp2": [round(_coerce_expr(cp2[0], penv), 3), round(_coerce_expr(cp2[1], penv), 3)],
                                "to": [round(_coerce_expr(to[0], penv), 3), round(_coerce_expr(to[1], penv), 3)],
                            },
                        }
                    )
                elif t == "ARC":
                    # placeholder: ARC can be implemented later (bulge or segmented)
                    paths.append({"type": "ARC", "data": {"raw": cmd.get("expr")}})
                elif t == "CLOSE":
                    paths.append({"type": "CLOSE", "data": {}})

            # notches
            notches = []
            for n in p.get("notches", []):
                nx = round(_coerce_expr(n[0], penv), 3)
                ny = round(_coerce_expr(n[1], penv), 3)
                notches.append([nx, ny, n[2]])

            # grain
            grain = None
            if p.get("grain"):
                g = p["grain"]
                gx1 = round(_coerce_expr(g[0], penv), 3)
                gy1 = round(_coerce_expr(g[1], penv), 3)
                gx2 = round(_coerce_expr(g[2], penv), 3)
                gy2 = round(_coerce_expr(g[3], penv), 3)
                grain = [[gx1, gy1], [gx2, gy2]]

            pieces_out.append(
                {"name": p["name"], "paths": paths, "notches": notches, "drills": [], "grain": grain}
            )

        payload = {"units": "mm", "pieces": pieces_out}
        out.write_text(json.dumps(payload, indent=2))
        typer.echo(f"Wrote base geometry from block to {out}")
        return

    # ---- Demo DSL fallback (for sanity-checking pipeline) ----
    demo_dsl = """PIECE front_panel_A
MOVE 0,0
LINE 0,520
LINE 140,520
LINE 140,0
CLOSE
NOTCH 20,520 "CF hem"
GRAIN 30,20 -> 30,300
SA 8
END
"""
    pieces = parse_dsl(demo_dsl)
    payload = {"units": "mm", "pieces": [_piece_to_json(pc) for pc in pieces]}
    out.write_text(json.dumps(payload, indent=2))
    typer.echo(f"Wrote base geometry (demo DSL) to {out}")


@app.command()
def construct(
    inp: Path = typer.Option(..., exists=True, dir_okay=False, help="Base JSON from `draft`"),
    options: Path = typer.Option(..., exists=True, help="Options YAML (e.g., seam_allowance)"),
    out: Path = typer.Option(..., help="Output constructed JSON"),
):
    """
    Apply construction transforms (for now: seam allowance).
    - Reads `seam_allowance` from options.yml (mm).
    - Adds `sa_paths` (MOVE/LINE list) to each piece.
    """
    import yaml

    out.parent.mkdir(parents=True, exist_ok=True)
    data = json.loads(Path(inp).read_text())
    opts = yaml.safe_load(Path(options).read_text()) or {}
    sa_mm = float(opts.get("seam_allowance", 0))

    for p in data.get("pieces", []):
        if sa_mm > 0:
            sa_poly = offset_piece(p, sa_mm)
            if sa_poly:
                cmds = [{"type": "MOVE", "data": {"to": [sa_poly[0][0], sa_poly[0][1]}}}]
                for x, y in sa_poly[1:]:
                    cmds.append({"type": "LINE", "data": {"to": [x, y]}})
                p["sa_paths"] = cmds

    Path(out).write_text(json.dumps(data, indent=2))
    typer.echo(f"Wrote constructed geometry to {out}")


@app.command()
def package(
    inp: Path = typer.Option(..., exists=True, dir_okay=False, help="Constructed JSON"),
    out: Path = typer.Option(..., help="Output directory for SVG preview"),
):
    """
    Package to SVG (simple layout).
    Writes one SVG combining pieces for quick visual checks.
    """
    out.mkdir(parents=True, exist_ok=True)
    data = json.loads(Path(inp).read_text())

    # Reconstruct minimal Piece objects for SVG helper
    pieces: List[Piece] = []
    for p in data["pieces"]:
        piece = Piece(name=p["name"])
        for cmd in p["paths"]:
            piece.paths.append(PathCmd(cmd["type"], cmd["data"]))
        # (notches/grain are not drawn by the basic SVG helper yet)
        pieces.append(piece)

    svg_path = out / "pattern.svg"
    pieces_to_svg(pieces, str(svg_path))
    typer.echo(f"Wrote {svg_path}")


@app.command("export-dxf")
def export_dxf_cmd(
    inp: Path = typer.Option(..., exists=True, dir_okay=False, help="Constructed JSON"),
    out: Path = typer.Option(..., help="Output DXF path"),
    units: str = typer.Option("mm", help="Units for $INSUNITS (mm|in|unitless)"),
    splines: bool = typer.Option(False, help="Emit SPLINE entities for curves"),
    flatten_tol: float = typer.Option(0.2, help="Bezier flatten tolerance (mm) when not using splines"),
    arcs: str = typer.Option("segment", help="ARC handling: bulge|segment (future)"),
):
    """
    Export constructed JSON to DXF (AC1018) with layers:
    CUT / SA / NOTCH / DRILL / GRAIN / TEXT
    """
    from ..packaging.dxf_exporter import export_dxf  # import here to keep CLI import light

    data = json.loads(Path(inp).read_text())
    out.parent.mkdir(parents=True, exist_ok=True)
    path = export_dxf(
        data,
        str(out),
        units=units,
        splines=splines,
        flatten_tol=flatten_tol,
        arcs_mode=arcs,
    )
    typer.echo(f"Wrote DXF: {path}")


if __name__ == "__main__":
    app()
