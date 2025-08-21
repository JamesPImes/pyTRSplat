from __future__ import annotations
import json
import os
from pathlib import Path

from PIL import ImageFont

__all__ = [
    'Settings',
]


class Settings:
    """
    Configure the look and behavior plats (e.g., size, colors, fonts,
    whether to write headers/tracts/etc.). Default and presets are
    available and customizable.

    Load a preset with ``Settings.preset('some_preset_name')``. List
    existing presets with ``Settings.list_presets()``. Save or alter
    presets with ``Settings.save_preset()``. Save configurations
    elsewhere with ``.to_json(some/path/file.json)`` and load them with
    ``Settings.from_json(some/path/file.json)``.

    .. note::

        To establish a separate directory for custom presets for a
        specific project, change the class variable of
        ``Settings.PRESET_DIRECTORY`` for that project before loading
        any presets. Or presets can be loaded individually from any
        directory or filepath with ``Settings.from_json()``.

    To change font size and/or typeface, be sure to use ``.set_font()``.
    """
    SETTINGS_DIR = Path(os.path.dirname(__file__))

    TYPEFACES = {
        # 'Arial'-like font
        'Sans-Serif':
            SETTINGS_DIR / "_fonts" / "LiberationSans-Regular.ttf",
        'Sans-Serif (Bold)':
            SETTINGS_DIR / "_fonts" / "LiberationSans-Bold.ttf",
        'Sans-Serif (Bold-Italic)':
            SETTINGS_DIR / "_fonts" / "LiberationSans-BoldItalic.ttf",
        'Sans-Serif (Italic)':
            SETTINGS_DIR / "_fonts" / "LiberationSans-Italic.ttf",

        # 'Times New Roman'-like font
        'Serif':
            SETTINGS_DIR / "_fonts" / "LiberationSerif-Regular.ttf",
        'Serif (Bold)':
            SETTINGS_DIR / "_fonts" / "LiberationSerif-Bold.ttf",
        'Serif (Bold-Italic)':
            SETTINGS_DIR / "_fonts" / "LiberationSerif-BoldItalic.ttf",
        'Serif (Italic)':
            SETTINGS_DIR / "_fonts" / "LiberationSerif-Italic.ttf",

        # 'Courier'-like font
        'Mono':
            SETTINGS_DIR / "_fonts" / "LiberationMono-Regular.ttf",
        'Mono (Bold)':
            SETTINGS_DIR / "_fonts" / "LiberationMono-Bold.ttf",
        'Mono (Bold-Italic)':
            SETTINGS_DIR / "_fonts" / "LiberationMono-BoldItalic.ttf",
        'Mono (Italic)':
            SETTINGS_DIR / "_fonts" / "LiberationMono-Italic.ttf",
    }

    DEFAULT_TYPEFACE = TYPEFACES['Sans-Serif']

    # Where we'll look for .json files of preset data.
    PRESET_DIRECTORY = SETTINGS_DIR / "_presets"

    # Default page-size dimensions.
    LETTER_72_PPI = (612, 792)
    LETTER_200_PPI = (1700, 2200)
    LETTER_300_PPI = (1700, 3300)
    LEGAL_72_PPI = (612, 1008)
    LEGAL_200_PPI = (1700, 2800)
    LEGAL_300_PPI = (2550, 4200)

    # Fully opaque.
    RGBA_RED = (255, 0, 0, 255)
    RGBA_GREEN = (0, 255, 0, 255)
    RGBA_BLUE = (0, 0, 255, 255)
    RGBA_BLACK = (0, 0, 0, 255)
    RGBA_WHITE = (255, 255, 255, 255)

    # Partially translucent.
    RGBA_RED_OVERLAY = (255, 0, 0, 100)
    RGBA_GREEN_OVERLAY = (0, 255, 0, 100)
    RGBA_BLUE_OVERLAY = (0, 0, 255, 100)
    RGBA_BLACK_OVERLAY = (0, 0, 0, 100)
    RGBA_WHITE_OVERLAY = (255, 255, 255, 100)

    _TYPEFACE_ATTS = (
        'headerfont_typeface',
        'footerfont_typeface',
        'secfont_typeface',
        'lotfont_typeface',
    )

    # Attributes that are included when outputting a save/loading a
    # Settings object to/from JSON. Includes a description of each attribute.
    _SET_ATTS = {
        # Dimensions, lines, fills, etc.
        'dim':
            'Dimensions of the plat in px.',
        'qq_fill_rgba':
            'RGBA value for filled aliquots',
        'sec_length_px':
            'Size of a section line in px',
        'line_stroke':
            'A dict of stroke sizes to use for section lines and subdivisions',
        'line_rgba':
            'A dict of RGBA color codes to use for section lines and subdivisions',
        'min_depth':
            'How many times to divide each section on the plat. (2 -> QQs; 3 -> QQQs; etc.)',
        'max_depth':
            'How small to allow aliquots (2 -> anything smaller than QQ increases to QQ)',
        'centerbox_dim':
            'How much of the center of the section white out, in px',
        'lot_num_offset_px':
            'How far off the top-left corner of a QQ to write the lot number',
        # Fonts.
        'headerfont_typeface':
            'Path to .ttf file for font to use for header.',
        'footerfont_typeface':
            'Path to .ttf file for font to use for footer.',
        'secfont_typeface':
            'Path to .ttf file for font to use for section numbers.',
        'lotfont_typeface':
            'Path to .ttf file for font to use for lot numbers.',
        'headerfont_size':
            'Font size for header.',
        'footerfont_size':
            'Font size for footer.',
        'secfont_size':
            'Font size for section numbers.',
        'lotfont_size':
            'Font size for lot numbers.',
        'headerfont_rgba':
            'RGBA for header font.',
        'footerfont_rgba':
            'RGBA for footer font.',
        'secfont_rgba':
            'RGBA for section number font.',
        'lotfont_rgba':
            'RGBA for lot number font.',
        'warningfont_rgba':
            'RGBA for warnings font.',
        # Margins.
        'body_marg_top_y':
            'Distance between top of image and top of first row of sections.',
        # Body's left/right margins are determined by `.dim` and `.sec_length_px`.
        'header_px_above_body':
            'Distance in px between the top section line and the header',
        'footer_px_below_body':
            'How many px below the plat grid to begin writing in the footer',
        'footer_marg_left_x':
            'Left margin of the footer (in px)',
        'footer_marg_right_x':
            'Right margin of the footer (in px)',
        'footer_marg_bottom_y':
            'Bottom margin of the footer',
        'footer_px_between_lines':
            'How many px between lines of text in the footer',
        # Text behavior.
        'write_header':
            'Whether to write the default header (its Twp/Rge)',
        'short_header':
            "Whether to shorten the default header to format 'T154N-R97W'",
        'write_tracts':
            'Whether to write tract descriptions in the footer.',
        'write_section_numbers':
            'Whether to write section numbers',
        'write_lot_numbers':
            'Whether to write lot numbers',
    }

    def __init__(self):
        # Dimensions of the image.
        self.dim = Settings.LETTER_200_PPI
        self.qq_fill_rgba = Settings.RGBA_BLUE_OVERLAY
        self.sec_length_px = 200
        self.line_stroke: dict[int, int] = {
            -1: 4,  # Township border
            0: 3,  # sec line
            1: 3,  # half line
            2: 1,  # quarter line
            3: 1,  # quarter-quarter line
            None: 1  # default for all others
        }
        # RGBA values for color of various sec/Q lines
        self.line_rgba = {
            -1: Settings.RGBA_BLACK,  # Township border
            0: Settings.RGBA_BLACK,  # sec line
            1: Settings.RGBA_BLACK,  # half line
            2: (128, 128, 128, 140),  # quarter line
            3: (128, 128, 128, 60),  # quarter-quarter line
            None: (196, 196, 196, 100)  # default for all others
        }
        self.min_depth = 2
        self.max_depth = None
        self.centerbox_dim = 48
        self.lot_num_offset_px = 6

        # Font typeface, size, and RGBA values.
        # IMPORTANT: To change font size and/or typeface, be sure to use
        # `.set_font()`, because it creates a new ImageFont object.
        # (RGBA can be set directly, or with `.set_font()` -- because
        # color is not encoded in a ImageFont object)
        self.headerfont_typeface = Settings.DEFAULT_TYPEFACE
        self.footerfont_typeface = Settings.DEFAULT_TYPEFACE
        self.secfont_typeface = Settings.DEFAULT_TYPEFACE
        self.lotfont_typeface = Settings.DEFAULT_TYPEFACE
        self.headerfont_size = 64
        self.footerfont_size = 28
        self.secfont_size = 36
        self.lotfont_size = 14
        self.headerfont_rgba = Settings.RGBA_BLACK
        self.footerfont_rgba = Settings.RGBA_BLACK
        self.secfont_rgba = Settings.RGBA_BLACK
        self.lotfont_rgba = Settings.RGBA_BLACK
        # Color to use to write warnings/errors (not tied to any specific font)
        self.warningfont_rgba = Settings.RGBA_RED
        # Default font objects will be set by `._update_fonts()` shortly.
        self.headerfont: ImageFont = None
        self.footerfont: ImageFont = None
        self.secfont: ImageFont = None
        self.lotfont: ImageFont = None
        self._update_fonts()

        # Margins.
        self.body_marg_top_y = 180
        self.header_px_above_body = 15
        self.footer_marg_bottom_y = 80
        self.footer_marg_left_x = 100
        self.footer_marg_right_x = 100
        self.footer_px_below_body = 40
        self.footer_px_between_lines = 10

        # Whether to write these labels / text:
        self.write_header = True
        self.short_header = False
        self.write_tracts = True
        self.write_section_numbers = True
        self.write_lot_numbers = False

    def get(self, att, default=None):
        """Get an attribute by its name."""
        if hasattr(self, att):
            return getattr(self, att)
        return default

    @property
    def grid_xy(self):
        """Get the top-left coord of the section grid (the body of a plat)."""
        twp_width_px = self.sec_length_px * 6
        w = self.dim[0]
        x = (w - twp_width_px) // 2
        y = self.body_marg_top_y
        return (x, y)

    def to_dict(self) -> dict:
        """Convert the settings to a dict."""
        d = {att: getattr(self, att) for att in self._SET_ATTS.keys()}
        for att in self._TYPEFACE_ATTS:
            fp = d[att]
            fp = _abs_path_to_rel(fp)
            d[att] = fp
        return d

    def to_json(self, filepath: Path) -> None:
        """Save settings to a ``.json`` file at the ``filepath``."""
        d = self.to_dict()
        with open(filepath, 'w', newline='') as f:
            json_str = json.dumps(d, indent=2)
            f.write(json_str)
        return None

    @classmethod
    def from_dict(cls, d: dict) -> Settings:
        """Convert a dict to a ``Settings`` object."""
        config = cls()
        for att in cls._SET_ATTS.keys():
            setattr(config, att, d[att])
        config._update_fonts()
        return config

    @classmethod
    def from_json(cls, filepath: Path) -> Settings:
        """Load settings from a ``.json`` file at the ``filepath``."""
        with open(filepath, 'r') as f:
            d = json.load(fp=f)
        line_stroke = {}
        for k, v in d['line_stroke'].items():
            try:
                k = int(k)
            except ValueError:
                k = None
            line_stroke[k] = v
        d['line_stroke'] = line_stroke
        line_rgba = {}
        for k, v in d['line_rgba'].items():
            try:
                k = int(k)
            except ValueError:
                k = None
            line_rgba[k] = tuple(v)
        d['line_rgba'] = line_rgba
        for k, v in d.items():
            if isinstance(v, list):
                v = tuple(v)
            d[k] = v
        # Ensure typeface paths are appropriate for current OS.
        for att in Settings._TYPEFACE_ATTS:
            v = d[att]
            v = v.replace('\\', '/')
            path_components = [v]
            if '/' in v:
                path_components = v.split('/')
            v = os.path.join(*path_components)
            d[att] = v
        return cls.from_dict(d)

    def set_font(
            self,
            purpose: str,
            size: int = None,
            typeface: str | Path = None,
            rgba: tuple[int, int, int, int] = None
    ) -> None:
        """
        Set the font for the specified ``purpose``. Any unspecified
        parameters will remain unchanged.

        :param purpose:
            One of ``'header'``, ``'footer'``, ``'sec'``, or ``'lot'``.

        :param size:
            Int of font size.

        :param typeface:
            A string specifying which typeface to use, as one of:

            - Relative path (str) to a stock font (with extension
              ``.ttf``) located in the
              ``pytrsplat/plat_gen/plat_settings/_fonts/`` directory.

              Example::

                  '_fonts/LiberationSans-Bold.ttf'

            - Absolute path (str) to a font (with extension ``.ttf``)
              located anywhere.

            - A key (str) in the ``Settings.TYPEFACES`` dict, which
              maps keys to absolute paths to ``.ttf`` fonts.
              Example: ``'Sans-Serif (Bold)'``

        :param rgba:
            4-tuple of RGBA color values (0–255).
        """
        purpose = purpose.lower()
        if purpose not in ('header', 'footer', 'sec', 'lot'):
            raise ValueError(f"Illegal `purpose`: {purpose!r}")
        if rgba is not None:
            setattr(self, f"{purpose}font_rgba", rgba)

        # If `typeface` and `size` are BOTH None, the ImageFont object
        # won't change. (RGBA does not get encoded in ImageFont object.)
        if typeface is None and size is None:
            return
        if typeface is None:
            typeface = getattr(self, f"{purpose}font_typeface")
        if size is None:
            size = getattr(self, f"{purpose}font_size")

        # If typeface was passed as font name (i.e. Settings.TYPEFACES
        # key), set it to the corresponding absolute path.
        if typeface in Settings.TYPEFACES.keys():
            typeface = Settings.TYPEFACES[typeface]
        self._create_set_font(purpose, size, typeface)
        setattr(self, f"{purpose}font_size", size)
        setattr(self, f"{purpose}font_typeface", typeface)
        return None

    def _create_set_font(
            self, purpose: str, size: int, typeface: str | Path) -> ImageFont:
        """
        Construct an ``ImageFont`` object from the specified ``size``
        and ``typeface`` (a filepath to a ``.ttf`` file), and set it for
        the specified ``purpose`` (being ``'header'``, ``'footer'``,
        ``'sec'``, or ``'lot'``).
        """
        purpose = purpose.lower()
        if purpose not in ('header', 'footer', 'sec', 'lot'):
            raise ValueError(f"Illegal `purpose`: {purpose!r}")
        try:
            # Try as absolute path first.
            fnt = ImageFont.truetype(typeface, size)
        except OSError as no_font_error:
            # Try instead as relative path (within 'pytrsplat/plat_gen/plat_settings/'.)
            try:
                fnt = ImageFont.truetype(_rel_path_to_abs(typeface), size)
            except OSError:
                raise no_font_error
        setattr(self, f'{purpose}font', fnt)
        return fnt

    def _update_fonts(self):
        """
        Construct ``ImageFont`` objects from the current settings, and
        set them to the appropriate attributes.
        """
        for purpose in ('header', 'footer', 'sec', 'lot'):
            size = getattr(self, f"{purpose}font_size")
            typeface = getattr(self, f"{purpose}font_typeface")
            self._create_set_font(purpose, size, typeface)
        return None

    @classmethod
    def preset(cls, name: str) -> Settings:
        """
        Load a saved preset. The specified preset ``name`` must exist in
        the existing presets, which can be listed with
        ``Settings.list_presets()``.
        """
        fp = Settings.PRESET_DIRECTORY / f"{name}.json"
        return cls.from_json(fp)

    @classmethod
    def list_presets(cls) -> list:
        """
        Get a sorted list of current presets in the preset directory
        (each returned as all lowercase).
        """
        files = os.listdir(cls.PRESET_DIRECTORY)
        presets = []
        for f in files:
            if f.lower().endswith('.json'):
                presets.append(f.lower()[:-4])
        presets.sort()
        return presets

    def save_preset(self, name: str):
        """Save this Settings object as a preset (with the name first
        converted to all lowercase)."""
        fp = self.PRESET_DIRECTORY / f"{name.lower()}.json"
        self.to_json(fp)
        return None

    @classmethod
    def restore_default(cls) -> Settings:
        """
        Restore the ``'default'`` preset ``Setting`` object to the
        original, hard-coded default.
        """
        st = Settings()
        st.save_preset('default')
        return st

    @classmethod
    def restore_presets(cls):
        """
        Restore the original presets. (Does not affect any presets
        created by a user.)
        """
        cls.restore_default()
        letter = cls.preset('default')
        letter.qq_fill_rgba = (0, 0, 255, 100)
        letter.save_preset('letter')

        letter.qq_fill_rgba = (68, 68, 68, 100)
        letter.warningfont_rgba = (68, 68, 68, 255)
        letter.save_preset('letter_gray')

        legal = cls.preset('letter')
        legal.dim = (1700, 2800)
        legal.save_preset('legal')

        legal_gray = cls.preset('letter_gray')
        legal_gray.dim = (1700, 2800)
        legal_gray.save_preset('legal_gray')

        sq_l = cls.preset('default')
        sq_l.dim = (1200, 1200)
        sq_l.headerfont_size = 48
        sq_l.footerfont_size = 14
        sq_l.secfont_size = 24
        sq_l.lotfont_size = 12
        sq_l.body_marg_top_y = 120
        sq_l.footer_marg_bottom_y = 20
        sq_l.header_px_above_body = 18
        sq_l.footer_marg_left_x = 20
        sq_l.footer_marg_right_x = 20
        sq_l.footer_px_below_body = 40
        sq_l.footer_px_between_lines = 7
        sq_l.sec_length_px = 160
        sq_l.line_stroke = {
            -1: 3,
            0: 1,
            1: 1,
            2: 1,
            3: 1,
            None: 1
        }
        sq_l.line_rgba[1] = (64, 64, 64, 255)
        for n in (2, 3, None):
            sq_l.line_rgba[n] = (196, 196, 196, 255)
        sq_l.write_tracts = False
        sq_l.write_lot_numbers = False
        sq_l.centerbox_dim = 48
        sq_l.save_preset('square_l')

        sq_m = sq_l
        sq_m.dim = (560, 560)
        sq_m.headerfont_size = 20
        sq_m.footerfont_size = 14
        sq_m.secfont_size = 14
        sq_m.lotfont_size = 1
        sq_m.body_marg_top_y = 40
        sq_m.header_px_above_body = 4
        sq_m.sec_length_px = 80
        sq_m.line_rgba[1] = (128, 128, 128, 255)
        for n in (2, 3, None):
            sq_m.line_rgba[n] = (230, 230, 230, 255)
        sq_m.centerbox_dim = 24
        sq_m.save_preset('square_m')

        sq_s = sq_m
        sq_s.dim = (416, 416)
        sq_s.headerfont_size = 18
        sq_s.footerfont_size = 14
        sq_s.secfont_size = 12
        sq_s.lotfont_size = 12
        sq_s.secfont_rgba = (128, 128, 128, 255)
        sq_s.footer_marg_bottom_y = 14
        sq_s.header_px_above_body = 3
        sq_s.footer_marg_left_x = 14
        sq_s.footer_marg_right_x = 14
        sq_s.footer_px_below_body = 40
        sq_s.sec_length_px = 56
        sq_s.line_stroke[-1] = 2
        sq_s.centerbox_dim = 20
        sq_s.save_preset('square_s')

        sq_tn = sq_s
        sq_tn.dim = (216, 216)
        sq_tn.headerfont_size = 10
        sq_tn.footerfont_size = 8
        sq_tn.secfont_size = 10
        sq_tn.lotfont_size = 1
        sq_tn.secfont_rgba = (64, 64, 64, 255)
        sq_tn.body_marg_top_y = 12
        sq_tn.header_px_above_body = 1
        sq_tn.footer_px_between_lines = 6
        sq_tn.sec_length_px = 32
        sq_tn.write_header = False
        sq_tn.centerbox_dim = 12
        sq_tn.save_preset('square_tiny')

        mp = Settings.preset('default')
        mp.sec_length_px = 120
        mp.body_marg_top_y = 36
        mp.short_header = True
        mp.set_font(
            purpose='header',
            rgba=(192, 192, 192, 255),
            typeface='Mono (Bold)',
            size=72
        )
        mp.set_font(
            purpose='sec',
            size=24
        )
        mp.line_stroke[-1] = 8
        mp.line_stroke[1] = 1
        mp.line_stroke[2] = 1
        mp.centerbox_dim = 38
        mp.save_preset('megaplat_default')

        mp_s = mp
        mp_s.body_marg_top_y = 14
        mp_s.sec_length_px = 64
        mp_s.short_header = True
        mp_s.set_font(
            purpose='header',
            rgba=(192, 192, 192, 255),
            typeface='Mono (Bold)',
            size=48
        )
        mp_s.set_font(
            purpose='sec',
            size=14
        )
        mp_s.line_stroke[-1] = 4
        mp_s.line_stroke[0] = 0
        mp_s.line_stroke[1] = 0
        mp_s.line_stroke[2] = 0
        mp_s.centerbox_dim = 20
        mp_s.save_preset('megaplat_s')
        return None


def _abs_path_to_rel(fp: str):
    """
    INTERNAL USE:

    Convert an absolute path that points to a file or directory within
    this module, into a relative path -- i.e. relative to the
    ``pytrsplat/plat_gen/plat_settings/`` dir.

    If ``fp`` is already a relative filepath, or is an absolute filepath
    to a different directory, this will return the original ``fp``.

    :param fp: Filepath to convert to relative filepath.
    :return: The filepath (str), relative to
        ``pytrsplat/plat_gen/plat_settings/`` (i.e. relative to the
        directory for this module).
    """
    fp = str(fp)
    settings_dir = str(Settings.SETTINGS_DIR)
    if fp.startswith(settings_dir):
        fp = fp.replace(settings_dir + '\\', '')
    return fp


def _rel_path_to_abs(fp: str | Path):
    """
    INTERNAL USE:

    Convert a relative path (within
    ``pytrsplat/plat_gen/plat_settings/``) to an absolute path, per the
    path of this module.

    :param fp: Relative filepath to convert to an absolute path.
    :return: A ``Path`` object for an absolute path.
    """
    return Settings.SETTINGS_DIR / fp


# Add setting attributes and descriptions to the Settings docstring.
docstring = Settings.__doc__
docstring = f"{docstring}\n\n**All configurable settings:**"
for att, description in Settings._SET_ATTS.items():
    docstring = f"{docstring}\n\n- ``{att}``: {description}"
# Add included typefaces to Settings docstring.
docstring = f"{docstring}\n\n**All included 'Liberation' typefaces:**\n\n"
docstring = (
    f"{docstring}You can use these with ``.set_font(purpose='header', "
    f"typeface='Mono (Bold)', size=48)``, for example.\n\n"
)
for typeface_name in Settings.TYPEFACES.keys():
    docstring = f"{docstring}\n\n- ``{typeface_name!r}``"

Settings.__doc__ = docstring
