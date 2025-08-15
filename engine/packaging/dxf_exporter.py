"""
DXF exporter (AC1018) for pattern pieces.

- Writes one DXF file per call.
- Units: sets $INSUNITS=4 (mm) when --units=mm.
- Geometry:
  * Per-piece outline emitted as LWPOLYLINE (default) or SPLINE if --splines=on.
  * CURVE segments (cubic Bezier) can be approximated to polylines with --flatten-tol.
  * ARC (if present) is approximated unless future ARC support is added to DSL.
- Layers: CUT/SA/NOTCH/DRILL/GRAIN/TEXT created BYLAYER.

Requires: ezdxf
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Tuple, Any, Optional
import math

try:
    import ezdxf  # type: ignore
except Exception as e:
    ezdxf = None

# ---------------- Utilities ----------------

def cubic_bezier(p0, p1, p2, p3, t: float):
    """Evaluate cubic Bezier at t [0,1]."""
    u = 1 - t
    return (
        u**3 * p0[0] + 3*u*u*t * p1[0] + 3*u*t*t * p2[0] + t**3 * p3[0],
        u**3 * p0[1] + 3*u*u*t * p1[1] + 3*u*t*t * p2[1] + t**3 * p3[1],
    )

def flatten_cubic(p0, p1, p2, p3, tol=0.2):
    """Adaptive flatten cubic Bezier into points, inc. endpoint p3."""
    pts = [p0, p3]
    # simple subdivision based on chord error; iterative for simplicity
    def subdivide(a,b,c,d):
        # midpoints
        ab = ((a[0]+b[0])/2,(a[1]+b[1])/2)
        bc = ((b[0]+c[0])/2,(b[1]+c[1])/2)
        cd = ((c[0]+d[0])/2,(c[1]+d[1])/2)
        abc = ((ab[0]+bc[0])/2,(ab[1]+bc[1])/2)
        bcd = ((bc[0]+cd[0])/2,(bc[1]+cd[1])/2)
        abcd = ((abc[0]+bcd[0])/2,(abc[1]+bcd[1])/2)
        return (a,ab,abc,abcd),(abcd,bcd,cd,d)
    stack = [(p0,p1,p2,p3)]
    out = [p0]
    while stack:
        a,b,c,d = stack.pop()
        # flatness metric: distance from control points to chord
        def dist(p, s, e):
            x0,y0 = p; x1,y1 = s; x2,y2 = e
            num = abs((y2-y1)*x0 - (x2-x1)*y0 + x2*y1 - y2*x1)
            den = math.hypot(x2-x1, y2-y1) or 1.0
            return num/den
        chord_tol = max(dist(b,a,d), dist(c,a,d))
        if chord_tol <= tol:
            out.append(d)
        else:
            left,right = subdivide(a,b,c,d)
            stack.append(right)
            stack.append(left)
    return out

# --------------- Export Core ----------------

def export_dxf(
    data: Dict[str, Any],
    out_path: str,
    units: str = "mm",
    splines: bool = False,
    flatten_tol: float = 0.2,
    arcs_mode: str = "segment",
    layer_map: Optional[Dict[str,str]] = None,
):
    if ezdxf is None:
        raise RuntimeError("ezdxf is not available. Install dependencies: pip install ezdxf")

    doc = ezdxf.new(dxfversion="AC1018")
    msp = doc.modelspace()

    # Units
    if units.lower() == "mm":
        doc.header["$INSUNITS"] = 4  # 4 = millimeters
    elif units.lower() == "in":
        doc.header["$INSUNITS"] = 1  # inches
    else:
        doc.header["$INSUNITS"] = 0  # unitless

    # Layers
    default_layers = {
        "CUT": {"color": 7},
        "SA": {"color": 1},
        "NOTCH": {"color": 3},
        "DRILL": {"color": 5},
        "GRAIN": {"color": 2},
        "TEXT": {"color": 8},
    }
    if layer_map:
        # remap names; colors remain default
        renamed = {}
        for k,v in default_layers.items():
            name = layer_map.get(k, k)
            renamed[name] = v
        default_layers = renamed
    for lname, opts in default_layers.items():
        if lname not in doc.layers:
            doc.layers.add(lname, color=opts.get("color", 7))

    def add_poly(points, layer):
        if not points:
            return
        # LWPOLYLINE with closed flag if endpoints equal (approx) or last segment is explicit CLOSE
        closed = (points[0] == points[-1])
        msp.add_lwpolyline(points, format="xy", dxfattribs={"layer": layer, "closed": closed})

    # Iterate pieces
    for piece in data.get("pieces", []):
        name = piece.get("name", "piece")
        layer_cut = "CUT"
        # Build a vertex list from MOVE/LINE/CURVE
        verts = []
        pen = None
        closed = False
        for cmd in piece.get("paths", []):
            typ = cmd["type"]
            dat = cmd.get("data", {})
            if typ == "MOVE":
                pen = tuple(dat["to"])
                verts.append(pen)
            elif typ == "LINE":
                if pen is None:
                    pen = tuple(dat["to"])
                    verts.append(pen)
                else:
                    p = tuple(dat["to"])
                    verts.append(p); pen = p
            elif typ == "CURVE":
                # cubic Bezier from current pen to "to" with cp1, cp2
                if pen is None:
                    continue
                p0 = pen
                p1 = tuple(dat["cp1"]); p2 = tuple(dat["cp2"]); p3 = tuple(dat["to"])
                if splines:
                    # use flattened fit points to make a spline (ok for most CAM)
                    pts = flatten_cubic(p0,p1,p2,p3, tol=flatten_tol)
                    # create spline with fit_points; ensure at least 4 points
                    if len(pts) >= 4:
                        msp.add_spline(fit_points=pts, dxfattribs={"layer": layer_cut})
                    else:
                        add_poly(pts, layer_cut)
                    pen = p3
                    verts.append(p3)
                else:
                    pts = flatten_cubic(p0,p1,p2,p3, tol=flatten_tol)
                    # append without duplicating starting point
                    for q in pts[1:]:
                        verts.append(q)
                    pen = p3
            elif typ == "ARC":
                # Not yet: approximate to polyline
                # Future: compute bulge for LWPOLYLINE if arcs_mode == "bulge"
                # For now, treat as pass (handled in future when DSL supplies endpoints/radii)
                pass
            elif typ == "CLOSE":
                closed = True
        # Close polyline if needed
        if verts and (closed and verts[0] != verts[-1]):
            verts.append(verts[0])
        if verts:
            add_poly(verts, layer_cut)

        # Notches
        for x,y,label in piece.get("notches", []):
            # small line tick to visualize notch
            size = 3.0
            msp.add_line((x - size, y), (x + size, y), dxfattribs={"layer":"NOTCH"})
            msp.add_line((x, y - size), (x, y + size), dxfattribs={"layer":"NOTCH"})
            msp.add_text(str(label), dxfattribs={"height": 2.5, "layer":"TEXT"}).set_pos((x+4, y+4))

        # Drills
        for x,y,label in piece.get("drills", []):
            msp.add_circle((x,y), radius=1.0, dxfattribs={"layer":"DRILL"})
            msp.add_text(str(label), dxfattribs={"height": 2.5, "layer":"TEXT"}).set_pos((x+4, y+4))

        # Grain
        grain = piece.get("grain") or []
        if len(grain) == 2:
            (x1,y1),(x2,y2) = grain
            msp.add_line((x1,y1),(x2,y2), dxfattribs={"layer":"GRAIN"})

        # Label
        msp.add_text(name, dxfattribs={"height": 5, "layer":"TEXT"}).set_pos((0, -10))

    # Save
    doc.saveas(out_path)
    return out_path
