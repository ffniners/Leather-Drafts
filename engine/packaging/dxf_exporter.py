from __future__ import annotations
from typing import List, Dict, Tuple, Any, Optional
import math
try:
    import ezdxf  # type: ignore
except Exception:
    ezdxf = None

def _dist_point_to_segment(p, a, b):
    x0,y0 = p; x1,y1 = a; x2,y2 = b
    dx,dy = x2-x1, y2-y1
    if dx==0 and dy==0:
        return math.hypot(x0-x1, y0-y1)
    t = ((x0-x1)*dx + (y0-y1)*dy) / (dx*dx + dy*dy)
    t = max(0, min(1, t))
    proj = (x1 + t*dx, y1 + t*dy)
    return math.hypot(x0-proj[0], y0-proj[1])

def flatten_cubic(p0, p1, p2, p3, tol=0.2):
    out = [p0]
    stack = [(p0,p1,p2,p3)]
    while stack:
        a,b,c,d = stack.pop()
        chord_err = max(_dist_point_to_segment(b,a,d), _dist_point_to_segment(c,a,d))
        if chord_err <= tol:
            out.append(d)
        else:
            ab = ((a[0]+b[0])/2,(a[1]+b[1])/2)
            bc = ((b[0]+c[0])/2,(b[1]+c[1])/2)
            cd = ((c[0]+d[0])/2,(c[1]+d[1])/2)
            abc = ((ab[0]+bc[0])/2,(ab[1]+bc[1])/2)
            bcd = ((bc[0]+cd[0])/2,(bc[1]+cd[1])/2)
            abcd = ((abc[0]+bcd[0])/2,(abc[1]+bcd[1])/2)
            stack.append((abcd,bcd,cd,d))
            stack.append((a,ab,abc,abcd))
    return out

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
        raise RuntimeError("ezdxf is not available. Install with: pip install ezdxf")

    doc = ezdxf.new(dxfversion="AC1018")
    msp = doc.modelspace()

    # Units
    if units.lower() == "mm":
        doc.header["$INSUNITS"] = 4
    elif units.lower() == "in":
        doc.header["$INSUNITS"] = 1
    else:
        doc.header["$INSUNITS"] = 0

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
        renamed = {}
        for k,v in default_layers.items():
            renamed[layer_map.get(k,k)] = v
        default_layers = renamed
    for lname, opts in default_layers.items():
        if lname not in doc.layers:
            doc.layers.add(lname, color=opts.get("color", 7))

    def add_poly(points, layer):
        if not points:
            return
        closed = (points[0] == points[-1])
        msp.add_lwpolyline(points, format="xy", dxfattribs={"layer": layer, "closed": closed})

    # Iterate pieces
    for piece in data.get("pieces", []):
        name = piece.get("name", "piece")

        # CUT outline
        verts = []
        pen = None
        closed = False
        for cmd in piece.get("paths", []):
            typ = cmd["type"]
            dat = cmd.get("data", {})
            if typ == "MOVE":
                pen = tuple(dat["to"]); verts.append(pen)
            elif typ == "LINE":
                p = tuple(dat["to"]); verts.append(p); pen = p
            elif typ == "CURVE":
                if pen is None: continue
                p0 = pen
                p1 = tuple(dat["cp1"]); p2 = tuple(dat["cp2"]); p3 = tuple(dat["to"])
                if splines:
                    pts = flatten_cubic(p0,p1,p2,p3, tol=flatten_tol)
                    if len(pts) >= 4:
                        msp.add_spline(fit_points=pts, dxfattribs={"layer":"CUT"})
                    else:
                        add_poly(pts, "CUT")
                    pen = p3; verts.append(p3)
                else:
                    pts = flatten_cubic(p0,p1,p2,p3, tol=flatten_tol)
                    verts.extend(pts[1:]); pen = p3
            elif typ == "CLOSE":
                closed = True
        if verts and (closed and verts[0] != verts[-1]):
            verts.append(verts[0])
        if verts:
            add_poly(verts, "CUT")

        # SA if present
        sa_cmds = piece.get("sa_paths", [])
        if sa_cmds:
            sa_verts = []
            for c in sa_cmds:
                if c["type"] == "MOVE":
                    sa_verts = [tuple(c["data"]["to"])]
                elif c["type"] == "LINE":
                    sa_verts.append(tuple(c["data"]["to"]))
            if sa_verts:
                msp.add_lwpolyline(sa_verts, format="xy", dxfattribs={"layer": "SA", "closed": True})

        # Notches
        for x,y,label in piece.get("notches", []):
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

    doc.saveas(out_path)
    return out_path
