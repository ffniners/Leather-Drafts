from typing import List
from .dsl_parser import Piece
import svgwrite

def pieces_to_svg(pieces: List[Piece], filename: str, page_size=(800, 600), margin=20):
    dwg = svgwrite.Drawing(filename, size=(page_size[0], page_size[1]))
    # naive layout: stack pieces vertically
    x_off, y_off = margin, margin
    for piece in pieces:
        path_cmds = []
        for cmd in piece.paths:
            if cmd.type == "MOVE":
                path_cmds.append(f"M {cmd.data['to'][0]} {cmd.data['to'][1]}")
            elif cmd.type == "LINE":
                path_cmds.append(f"L {cmd.data['to'][0]} {cmd.data['to'][1]}")
            elif cmd.type == "CURVE":
                cp1 = cmd.data['cp1']; cp2 = cmd.data['cp2']; to = cmd.data['to']
                path_cmds.append(f"C {cp1[0]},{cp1[1]} {cp2[0]},{cp2[1]} {to[0]},{to[1]}")
            elif cmd.type == "CLOSE":
                path_cmds.append("Z")
            else:
                # ARC and others not implemented
                pass
        piece_path = " ".join(path_cmds)
        g = dwg.g(transform=f"translate({x_off},{y_off})")
        g.add(dwg.path(d=piece_path, fill="none", stroke="black", stroke_width=1))
        # labels
        g.add(dwg.text(piece.name, insert=(0, -5), font_size="12px"))
        dwg.add(g)
        # move down for next piece
        y_off += 200
    dwg.save()
