from __future__ import annotations
from typing import Dict, Any, List, Tuple
import pyclipper

from ..geometry.flatten import piece_paths_to_polyline

SCALE = 1000.0  # scale to integer for Clipper

def _scale_path(path: List[Tuple[float,float]]):
    return [(int(round(x*SCALE)), int(round(y*SCALE))) for x,y in path]

def _unscale_path(path: List[Tuple[int,int]]):
    return [(x/SCALE, y/SCALE) for x,y in path]

def offset_piece(piece: Dict[str,Any], delta_mm: float, miter_limit: float=4.0) -> List[Tuple[float,float]]:
    """Offset a piece outline outward by delta_mm, returns a closed polyline."""
    base = piece_paths_to_polyline(piece, tol=0.2)
    if len(base) < 3:
        return []
    if base[0] != base[-1]:
        base = base + [base[0]]
    subj = [_scale_path(base)]
    co = pyclipper.PyclipperOffset(miter_limit=miter_limit, arc_tolerance=0.25*SCALE/1000.0)
    co.AddPaths(subj, pyclipper.JT_MITER, pyclipper.ET_CLOSEDPOLYGON)
    solution = co.Execute(delta_mm * SCALE)
    if not solution:
        return []
    # choose largest polygon
    largest = max(solution, key=lambda p: abs(pyclipper.Area(p)))
    out = _unscale_path(largest)
    if out and out[0] != out[-1]:
        out.append(out[0])
    return out
