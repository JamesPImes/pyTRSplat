__all__ = [
    'calc_midpt',
    'get_box',
    'get_box_outline',
]


def calc_midpt(xy: tuple[int, int], square_dim: int) -> tuple[int, int]:
    """
    Calculate the midpoint of a square, whose top-left coord is ``xy``
    and whose side length is ``square_dim`` (in px).
    """
    x, y = xy
    return x + square_dim // 2, y + square_dim // 2


def get_box(xy: tuple[int, int], dim: int) -> list[tuple[int, int]]:
    """
    Get the four sides of a box, with top-left at coord ``xy`` and each
    side being ``dim`` px long.
    """
    x, y = xy
    box = [
        (x, y),                 # top-left
        (x + dim, y),           # top-right
        (x + dim, y + dim),     # bottom-right
        (x, y + dim),           # bottom-left
    ]
    return box


def get_box_outline(xy: tuple[int, int], dim: int) -> list[list[tuple[int, int]]]:
    """Get the lines that make up the outline of a box."""
    x, y = xy
    box = [
        [(x, y), (x + dim, y)],                 # top
        [(x, y), (x, y + dim)],                 # left
        [(x + dim, y), (x + dim, y + dim)],     # right
        [(x, y + dim), (x + dim, y + dim)],     # bottom
    ]
    return box
