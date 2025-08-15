"""
Very small path DSL → internal representation.

PIECE <name>
MOVE x,y
LINE x,y
CURVE x1,y1 -> x2,y2 -> x3,y3
ARC x,y R=<radius> SWEEP=<CW|CCW> TO x,y   # placeholder (not implemented)
CLOSE
NOTCH x,y "label"
DRILL x,y "label"
GRAIN x1,y1 -> x2,y2
SA <millimeters>
END
"""
from dataclasses import dataclass, field
from typing import List, Tuple, Dict

@dataclass
class PathCmd:
    type: str
    data: dict

@dataclass
class Piece:
    name: str
    paths: List[PathCmd] = field(default_factory=list)
    notches: List[Tuple[float, float, str]] = field(default_factory=list)
    drills: List[Tuple[float, float, str]] = field(default_factory=list)
    grain: List[Tuple[float, float]] = field(default_factory=list)
    seam_allowance: float | None = None

def parse_dsl(text: str) -> List[Piece]:
    pieces: List[Piece] = []
    current: Piece | None = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("PIECE "):
            name = line.split(" ", 1)[1].strip()
            current = Piece(name=name)
            pieces.append(current)
            continue
        if line == "END":
            current = None
            continue
        if current is None:
            raise ValueError("Command outside of PIECE/END block")
        # Simple token parsing
        if line.startswith("MOVE "):
            x,y = map(float, line.split(" ",1)[1].split(","))
            current.paths.append(PathCmd("MOVE", {"to": [x,y]}))
        elif line.startswith("LINE "):
            x,y = map(float, line.split(" ",1)[1].split(","))
            current.paths.append(PathCmd("LINE", {"to": [x,y]}))
        elif line.startswith("CURVE "):
            # CURVE x1,y1 -> x2,y2 -> x3,y3
            body = line.split(" ",1)[1]
            a,b,c = [seg.strip() for seg in body.split("->")]
            x1,y1 = map(float, a.split(","))
            x2,y2 = map(float, b.split(","))
            x3,y3 = map(float, c.split(","))
            current.paths.append(PathCmd("CURVE", {"cp1":[x1,y1],"cp2":[x2,y2],"to":[x3,y3]}))
        elif line.startswith("ARC "):
            # Placeholder: treat ARC TO as LINE for now
            current.paths.append(PathCmd("ARC", {"raw": line}))
        elif line.startswith("CLOSE"):
            current.paths.append(PathCmd("CLOSE", {}))
        elif line.startswith("NOTCH "):
            coords, label = line[6:].split('"',1)
            x,y = map(float, coords.strip().split(","))
            lbl = label.rstrip('"').strip()
            current.notches.append((x,y,lbl))
        elif line.startswith("DRILL "):
            coords, label = line[6:].split('"',1)
            x,y = map(float, coords.strip().split(","))
            lbl = label.rstrip('"').strip()
            current.drills.append((x,y,lbl))
        elif line.startswith("GRAIN "):
            body = line.split(" ",1)[1]
            a,b = [seg.strip() for seg in body.split("->")]
            x1,y1 = map(float, a.split(","))
            x2,y2 = map(float, b.split(","))
            current.grain = [(x1,y1),(x2,y2)]
        elif line.startswith("SA "):
            current.seam_allowance = float(line.split(" ",1)[1])
        else:
            raise ValueError(f"Unknown line: {line}")
    return pieces
