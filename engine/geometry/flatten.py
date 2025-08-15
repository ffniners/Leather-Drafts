from __future__ import annotations
from typing import List, Tuple, Dict, Any
import math

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
    """Adaptive subdivision of a cubic Bezier to a polyline."""
    out = [p0]
    stack = [(p0,p1,p2,p3)]
    while stack:
        a,b,c,d = stack.pop()
        chord_err = max(_dist_point_to_segment(b,a,d), _dist_point_to_segment(c,a,d))
        if chord_err <= tol:
            out.append(d)
        else:
            # de Casteljau subdivision
            ab = ((a[0]+b[0])/2,(a[1]+b[1])/2)
            bc = ((b[0]+c[0])/2,(b[1]+c[1])/2)
            cd = ((c[0]+d[0])/2,(c[1]+d[1])/2)
            abc = ((ab[0]+bc[0])/2,(ab[1]+bc[1])/2)
            bcd = ((bc[0]+cd[0])/2,(bc[1]+cd[1])/2)
            abcd = ((abc[0]+bcd[0])/2,(abc[1]+bcd[1])/2)
            stack.append((abcd,bcd,cd,d))
            stack.append((a,ab,abc,abcd))
    return out

def piece_paths_to_polyline(piece: Dict[str,Any], tol: float=0.2) -> List[Tuple[float,float]]:
    """Flatten DSL path commands into a closed polyline (if CLOSE present)."""
    verts: List[Tuple[float,float]] = []
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
            if pen is None:
                continue
            p0 = pen
            p1 = tuple(dat["cp1"]); p2 = tuple(dat["cp2"]); p3 = tuple(dat["to"])
            pts = flatten_cubic(p0,p1,p2,p3, tol=tol)
            verts.extend(pts[1:])
            pen = p3
        elif typ == "CLOSE":
            closed = True
        # ARC TODO: approximate when ARC is implemented
    if closed and verts and verts[0] != verts[-1]:
        verts.append(verts[0])
    return verts
