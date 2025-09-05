from __future__ import annotations
import json
import os
from pathlib import Path
from typing import Union

from PIL import ImageFont

from ._preset_hardcode import PRESET_HARDCODE

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
    # Where we'll look for .json files of preset data.
    PRESET_DIRECTORY = SETTINGS_DIR / "_presets"

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
        'lots_only_for_queue':
            'Limit the written lot numbers to sections in the queue.'
    }

    def __init__(self):
        # Dimensions of the image.
        self.dim = Settings.LETTER_200_PPI
        self.qq_fill_rgba = Settings.RGBA_BLUE_OVERLAY
        self.sec_length_px = 200
        self.line_stroke: dict[Union[int, None], int] = {
            -1: 4,  # Township border
            0: 3,  # sec line
            1: 3,  # half line
            2: 1,  # quarter line
            3: 1,  # quarter-quarter line
            None: 1  # default for all others
        }
        # RGBA values for color of various sec/Q lines
        self.line_rgba: dict[Union[int, None], tuple[int, int, int, int]] = {
            -1: Settings.RGBA_BLACK,  # Township border
            0: Settings.RGBA_BLACK,  # sec line
            1: Settings.RGBA_BLACK,  # half line
            2: (64, 64, 64, 96),  # quarter line
            3: (64, 64, 64, 24),  # quarter-quarter line
            None: (230, 230, 230, 24)  # default for all others
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
        self.lots_only_for_queue = False

        # This is not saved to .json, but is filled 'manually' if using layers.
        self._layer_qq_fill_rgba: dict[str, tuple[int, int, int, int]] = {}

    def _get_layer_qq_fill_rgba(self, layer_name: str) -> tuple[int, int, int, int]:
        """
        Get the fill RGBA for a given layer. If not found, use the
        configured ``settings.qq_fill_rgba``.
        """
        default = self.qq_fill_rgba
        return self._layer_qq_fill_rgba.get(layer_name, default)

    def set_layer_fill(
            self, layer_name: str, qq_fill_rgba: tuple[int, int, int, int]) -> None:
        """
        Set the aliquot fill color (RGBA) for a given layer.

        .. note::

            These values do not get saved with the ``.save_preset()``
            method and must be configured individually each time.

        :param layer_name: Name of the layer to set.
        :param qq_fill_rgba: RGBA of the color to use for aliquots on
            that layer.
        """
        self._layer_qq_fill_rgba[layer_name] = qq_fill_rgba
        return None

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

    def to_json(self, fp: Union[str, Path]) -> None:
        """Save settings to a ``.json`` file at the filepath ``fp``."""
        d = self.to_dict()
        with open(fp, 'w', newline='') as f:
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
    def from_json(cls, fp: Union[str, Path]) -> Settings:
        """Load settings from a ``.json`` file at the filepath ``fp``."""
        with open(fp, 'r') as f:
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
                if v[0] == '/':
                    # Put macOS's initial slash back in.
                    path_components.insert(0, '/')
            v = os.path.join(*path_components)
            d[att] = v
        return cls.from_dict(d)

    def set_font(
            self,
            purpose: str,
            size: int = None,
            typeface: Union[str, Path] = None,
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
            self, purpose: str, size: int, typeface_fp: Union[str, Path]) -> ImageFont:
        """
        Construct an ``ImageFont`` object from the specified ``size``
        and ``typeface_fp`` (a filepath to a ``.ttf`` file), and set it for
        the specified ``purpose`` (being ``'header'``, ``'footer'``,
        ``'sec'``, or ``'lot'``).
        """
        purpose = purpose.lower()
        if purpose not in ('header', 'footer', 'sec', 'lot'):
            raise ValueError(f"Illegal `purpose`: {purpose!r}")
        typeface_fp = Path(typeface_fp)
        try:
            # Try as absolute path first.
            fnt = ImageFont.truetype(typeface_fp, size)
        except OSError as no_font_error:
            # Try instead as relative path (within 'pytrsplat/plat_gen/plat_settings/'.)
            try:
                if not typeface_fp.is_absolute():
                    fnt = ImageFont.truetype(_rel_path_to_abs(typeface_fp), size)
                else:
                    raise
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
                presets.append(f.lower()[:-5])
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
        for preset_name, setting_vals in PRESET_HARDCODE.items():
            stn = Settings.from_dict(setting_vals)
            stn.save_preset(preset_name)
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


def _rel_path_to_abs(fp: Union[str, Path]):
    """
    INTERNAL USE:

    Convert a relative path (within
    ``pytrsplat/plat_gen/plat_settings/``) to an absolute path, per the
    path of this module.

    :param fp: Relative filepath to convert to an absolute path.
    :return: A ``Path`` object for an absolute path.
    """
    fp = Path(fp)
    if fp.is_absolute():
        return fp
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
