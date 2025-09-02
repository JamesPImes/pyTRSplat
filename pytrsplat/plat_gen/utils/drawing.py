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


def get_box_outline(
        xy: tuple[int, int], dim: int, extend_px=0) -> list[list[tuple[int, int]]]:
    """
    Get the lines that make up the outline of a box.
    :param xy: Top-left coord.
    :param dim: Dimensions of the box.
    :param extend_px: (Optional) Number of px to extend the lines at
        each corner. Defaults to ``0``.
    """
    x, y = xy
    if extend_px == 0:
        box = [
            [(x, y), (x + dim, y)],                 # top
            [(x, y), (x, y + dim)],                 # left
            [(x + dim, y), (x + dim, y + dim)],     # right
            [(x, y + dim), (x + dim, y + dim)],     # bottom
        ]
    else:
        box = [
            [(x - extend_px, y), (x + dim + extend_px, y)],                     # top
            [(x, y - extend_px), (x, y + dim + extend_px)],                     # left
            [(x + dim, y - extend_px), (x + dim, y + dim + extend_px + 1)],     # right
            [(x - extend_px, y + dim), (x + dim + extend_px + 1, y + dim)],     # bottom
        ]
    return box
