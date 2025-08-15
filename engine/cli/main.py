import json, sys
from pathlib import Path
import typer
from typing import Optional
from ..dsl.dsl_parser import parse_dsl, Piece
from ..dsl.to_svg import pieces_to_svg

app = typer.Typer(help="patternlab CLI (starter)")

@app.command()
def draft(recipe: Path = typer.Option(..., exists=True, help="Recipe YAML"),
          measurements: Path = typer.Option(..., exists=True, help="Measurements JSON"),
          out: Path = typer.Option(..., help="Output base JSON")):
    """
    Draft base geometry. Starter emits a tiny demo piece using DSL.
    """
    out.parent.mkdir(parents=True, exist_ok=True)
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
    # serialize to simple JSON
    payload = {"units":"mm","pieces":[piece.__dict__ for piece in pieces]}
    out.write_text(json.dumps(payload, indent=2))
    typer.echo(f"Wrote base geometry to {out}")

@app.command()
def construct(inp: Path = typer.Option(..., exists=True, dir_okay=False, help="Base JSON"),
              options: Path = typer.Option(..., exists=True, help="Options YAML"),
              out: Path = typer.Option(..., help="Output constructed JSON")):
    """
    Construction transforms placeholder: pass-through for now.
    """
    out.parent.mkdir(parents=True, exist_ok=True)
    data = json.loads(Path(inp).read_text())
    # TODO: add seam allowances, facings, overlays
    out.write_text(json.dumps(data, indent=2))
    typer.echo(f"Wrote constructed geometry to {out}")

@app.command()
def package(inp: Path = typer.Option(..., exists=True, dir_okay=False, help="Constructed JSON"),
            out: Path = typer.Option(..., help="Output directory")):
    """
    Package to SVG (simple layout). Writes one SVG combining pieces.
    """
    out.mkdir(parents=True, exist_ok=True)
    data = json.loads(Path(inp).read_text())
    # reconstruct Piece objects minimally
    pieces: list[Piece] = []
    for p in data["pieces"]:
        piece = Piece(name=p["name"])
        for cmd in p["paths"]:
            from ..dsl.dsl_parser import PathCmd
            piece.paths.append(PathCmd(cmd["type"], cmd["data"]))
        pieces.append(piece)
    svg_path = out / "pattern.svg"
    pieces_to_svg(pieces, str(svg_path))
    typer.echo(f"Wrote {svg_path}")

if __name__ == "__main__":
    app()


@app.command("export-dxf")
def export_dxf_cmd(inp: Path = typer.Option(..., exists=True, dir_okay=False, help="Constructed JSON"),
                   out: Path = typer.Option(..., help="Output DXF path"),
                   units: str = typer.Option("mm", help="Units for $INSUNITS (mm|in|unitless)"),
                   splines: bool = typer.Option(False, help="Emit SPLINE entities for curves"),
                   flatten_tol: float = typer.Option(0.2, help="Bezier flatten tolerance (mm)"),
                   arcs: str = typer.Option("segment", help="ARC handling: bulge|segment (future)")):
    """
    Export constructed JSON to DXF AC1018 with layers for CUT/SA/NOTCH/DRILL/GRAIN/TEXT.
    """
    data = json.loads(Path(inp).read_text())
    from ..packaging.dxf_exporter import export_dxf
    out.parent.mkdir(parents=True, exist_ok=True)
    path = export_dxf(data, str(out), units=units, splines=splines, flatten_tol=flatten_tol, arcs_mode=arcs)
    typer.echo(f"Wrote DXF: {path}")
