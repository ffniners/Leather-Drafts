from shapely.geometry import LineString
def has_self_intersections(coords):
    # Very naive self-intersection check; improve later.
    line = LineString(coords)
    return not line.is_simple
