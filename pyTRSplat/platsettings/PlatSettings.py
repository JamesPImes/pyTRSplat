# Copyright (c) 2020, James P. Imes, all rights reserved.

from PIL import ImageFont
import os


class Settings:
    """
    Configure the look and behavior of Plat and MultiPlat objects (e.g.,
    size, colors, fonts, whether to write headers/tracts/etc.). Default
    and presets are available and customizable.

    When a string is passed (as `preset=`) at init, it is assumed to be
    one of two things:
        -- the filepath to a saved .txt file of data that can be read
            into a Settings object, with the `._import_file()` method.
        -- the name of a saved preset (with no file extension), which
            will be loaded with the `._load_preset()` method.
    If neither of those is successful, a default Settings object will be
    initialized instead.

    A Settings object can be saved as a preset with the `.save_preset()`
    method (which will save as a .txt file in the directory stored as
    class variable `Settings.PRESET_DIRECTORY`).
    NOTE: File extension is NOT specified when saving/loading preset
        (the program handles that internally).
    NOTE ALSO: To establish custom presets for a specific project, we
        can change the class variable of Settings.PRESET_DIRECTORY for
        that project in the code before loading any presets.

    A list of currently saved presets can be accessed by calling
    `Settings.list_presets()`.

    A Settings object can be saved to a (non-preset) .txt file at a
    specified filepath with the `.save_to_file()` method.
    NOTE: The file extension MUST BE SPECIFIED when saving/loading to a
        .txt file that is not a preset.

    To change font size and/or typeface, be sure to use `.set_font()`.

    NOTE: If `preset=` is not specified, 'default' will be loaded. The
        settings of the 'default' preset can be changed by creating a
        Settings object and calling `.save_preset('default')`, and then
        these will be the settings loaded by default in the future.
        There is also a hard-coded default, which can be loaded by
        passing `preset=None`, and which can be restored to the
        'default' preset with the method `Settings._restore_default()`.
    """

    ####################################################################
    # IMPORTANT: To change font size and/or typeface for a given
    # Settings object, be sure to use `.set_font()`, rather than setting
    # those attributes directly. Otherwise, the ImageFont object (from
    # the PIL module) will not be updated, so the updated size/typeface
    # won't actually get used.
    #
    # However, the RGBA of the font can be set directly, or with
    # `.set_font()` -- because color does not get encoded in a ImageFont
    # object.
    ####################################################################

    SETTINGS_DIR = os.path.dirname(__file__)

    TYPEFACES = {
        # 'Arial'-like font
        'Sans-Serif':
            f'{SETTINGS_DIR}\\_fonts\\LiberationSans-Regular.ttf',
        'Sans-Serif (Bold)':
            f'{SETTINGS_DIR}\\_fonts\\LiberationSans-Bold.ttf',
        'Sans-Serif (Bold-Italic)':
            f'{SETTINGS_DIR}\\_fonts\\LiberationSans-BoldItalic.ttf',
        'Sans-Serif (Italic)':
            f'{SETTINGS_DIR}\\_fonts\\LiberationSans-Italic.ttf',

        # 'Times New Roman'-like font
        'Serif':
            f'{SETTINGS_DIR}\\_fonts\\LiberationSerif-Regular.ttf',
        'Serif (Bold)':
            f'{SETTINGS_DIR}\\_fonts\\LiberationSerif-Bold.ttf',
        'Serif (Bold-Italic)':
            f'{SETTINGS_DIR}\\_fonts\\LiberationSerif-BoldItalic.ttf',
        'Serif (Italic)':
            f'{SETTINGS_DIR}\\_fonts\\LiberationSerif-Italic.ttf',

        # 'Courier'-like font
        'Mono':
            f'{SETTINGS_DIR}\\_fonts\\LiberationMono-Regular.ttf',
        'Mono (Bold)':
            f'{SETTINGS_DIR}\\_fonts\\LiberationMono-Bold.ttf',
        'Mono (Bold-Italic)':
            f'{SETTINGS_DIR}\\_fonts\\LiberationMono-BoldItalic.ttf',
        'Mono (Italic)':
            f'{SETTINGS_DIR}\\_fonts\\LiberationMono-Italic.ttf'
    }

    DEFAULT_TYPEFACE = TYPEFACES['Sans-Serif']

    # Where we'll look for .txt files of preset data.
    PRESET_DIRECTORY = f'{SETTINGS_DIR}\\_presets\\'

    # Default page-size dimensions.
    LETTER_72ppi = (612, 792)
    LETTER_200ppi = (1700, 2200)
    LETTER_300ppi = (1700, 3300)
    LEGAL_72ppi = (612, 1008)
    LEGAL_200ppi = (1700, 2800)
    LEGAL_300ppi = (2550, 4200)

    # These are fully opaque
    RGBA_RED = (255, 0, 0, 255)
    RGBA_GREEN = (0, 255, 0, 255)
    RGBA_BLUE = (0, 0, 255, 255)
    RGBA_BLACK = (0, 0, 0, 255)
    RGBA_WHITE = (255, 255, 255, 255)

    # These are partially translucent:
    RGBA_RED_OVERLAY = (255, 0, 0, 100)
    RGBA_GREEN_OVERLAY = (0, 255, 0, 100)
    RGBA_BLUE_OVERLAY = (0, 0, 255, 100)
    RGBA_BLACK_OVERLAY = (0, 0, 0, 100)
    RGBA_WHITE_OVERLAY = (255, 255, 255, 100)

    # These attributes are string-type. When creating a Settings object
    # from a text file (or saving one to a text file), that data will
    # also be stored as text. But we don't want to interpret any other
    # attributes as strings, so we keep track here of the only attribs
    # that SHOULD be strings.
    __stringTypeAtts__ = [
        'headerfont_typeface', 'tractfont_typeface', 'secfont_typeface',
        'lotfont_typeface'
    ]

    # We want to strip `SETTINGS_DIR` from the filepath of typefaces
    # when saving presets / to custom file, and reattach it when reading
    # from file, so keep track of typefaces
    __typefaceAtts__ = [
        'headerfont_typeface', 'tractfont_typeface', 'secfont_typeface',
        'lotfont_typeface'
    ]

    # These are the attributes that will get included when outputting a
    # Settings object to text file (i.e. creating a preset).
    __setAtts__ = [
        'dim', 'headerfont_typeface', 'tractfont_typeface', 'secfont_typeface',
        'lotfont_typeface', 'headerfont_size', 'tractfont_size', 'secfont_size',
        'lotfont_size', 'headerfont_RGBA', 'tractfont_RGBA', 'secfont_RGBA',
        'lotfont_RGBA', 'y_top_marg','y_bottom_marg', 'y_header_marg',
        'x_text_left_marg', 'x_text_right_marg', 'y_px_before_tracts',
        'y_px_between_tracts', 'qq_side', 'sec_line_stroke', 'ql_stroke',
        'qql_stroke', 'sec_line_RGBA', 'ql_RGBA', 'qql_RGBA', 'qq_fill_RGBA',
        'centerbox_wh', 'lot_num_offset_px', 'write_header', 'write_tracts',
        'write_section_numbers', 'write_lot_numbers', 'paragraph_indent',
        'new_line_indent', 'justify_tract_text', 'warningfont_RGBA'
    ]

    def __init__(self, preset='default'):

        # If the 'default' preset was deleted or can't be accessed, try
        # resetting the 'default' preset to the original, hard-coded
        # default (i.e. `preset=None`). If that fails, then we set
        # `preset` to `None`, which will bypass trying to import from
        # .txt file altogether and just return the hard-coded defaults.
        if preset == 'default':
            try:
                if 'default' not in Settings.list_presets():
                    Settings._restore_default()
            except:
                preset = None

        # Dimensions of the image.
        self.dim = Settings.LETTER_200ppi

        # Font typeface, size, and RGBA values.
        # IMPORTANT: To change font size and/or typeface, be sure to use
        # `.set_font()`, because it creates a new ImageFont object.
        # (RGBA can be set directly, or with `.set_font()` -- because
        # color is not encoded in a ImageFont object)
        self.headerfont_typeface = Settings.DEFAULT_TYPEFACE
        self.tractfont_typeface = Settings.DEFAULT_TYPEFACE
        self.secfont_typeface = Settings.DEFAULT_TYPEFACE
        self.lotfont_typeface = Settings.DEFAULT_TYPEFACE
        self.headerfont_size = 64
        self.tractfont_size = 28
        self.secfont_size = 36
        self.lotfont_size = 12
        self.headerfont_RGBA = Settings.RGBA_BLACK
        self.tractfont_RGBA = Settings.RGBA_BLACK
        self.secfont_RGBA = Settings.RGBA_BLACK
        self.lotfont_RGBA = Settings.RGBA_BLACK
        # Color to use to write warnings/errors (not tied to any specific font)
        self.warningfont_RGBA = Settings.RGBA_RED

        # Default font objects will be set by `._update_fonts()` shortly.
        self.headerfont = None
        self.tractfont = None
        self.secfont = None
        self.lotfont = None

        # Construct ImageFont objects from the above settings:
        self._update_fonts()

        # Distance between top of image and top of first row of sections.
        self.y_top_marg = 180

        # Distance between top section line and the T&R written above it.
        self.y_header_marg = 15

        # Bottom margin below which tracts cannot be written
        self.y_bottom_marg = 80

        # px indent for tract text (from the left side of the image).
        self.x_text_left_marg = 100

        # px for tract text right margin (distance from right side of image
        # that we can write up to).
        self.x_text_right_marg = 100

        # Distance between bottom section line and the first tract text written.
        self.y_px_before_tracts = 40

        # Distance between lines of text when writing tracts.
        self.y_px_between_tracts = 10

        # Spaces to indent on new lines in tract text
        self.new_line_indent = 8

        self.qq_side = 50  # length of each side for a QQ in px
        self.sec_line_stroke = 3  # section-line stroke width in px
        self.ql_stroke = 2  # quarter line stroke width in px
        self.qql_stroke = 1  # quarter-quarter line stroke width in px

        # RGBA values for color of various sec/Q lines
        self.sec_line_RGBA = Settings.RGBA_BLACK
        self.ql_RGBA = Settings.RGBA_BLACK
        self.qql_RGBA = (128, 128, 128, 100)

        # RGBA value for QQ fill
        self.qq_fill_RGBA = Settings.RGBA_BLUE_OVERLAY

        # How wide the whited-out centerbox in each section should be:
        self.centerbox_wh = 60

        # How many px set in from top-left corner of QQ box to write lot numbers
        self.lot_num_offset_px = 6

        # Whether to write these labels / text:
        self.write_header = True
        self.write_tracts = True
        self.write_section_numbers = True
        self.write_lot_numbers = False

        # Tract-writing indents, in terms of spaces (characters, not px):
        self.paragraph_indent = 0
        self.new_line_indent = 8

        # Whether tract text should be justified
        self.justify_tract_text = True

        # If `preset` is specified as a string, we assume it is a preset
        # and attempt to load it as Settings data.
        if isinstance(preset, str):
            self._import_preset(preset)

    def deduce_biggest_char(self, font_purpose='tract') -> str:
        """
        Deduce which character is the widest, when written with the font
        currently set for the specified `font_purpose` (i.e. 'header',
        'tract', 'sec', or 'lot'). Returns that character.
        """

        # Confirm it's a legal font_purpose
        purposes = ['header', 'tract', 'sec', 'lot']
        if font_purpose not in purposes:
            raise ValueError(f"Possible `font_purposes` are: "
                             f"{', '.join(purposes)}; "
                             f"Attempted to check width of character in "
                             f"font for purpose '{font_purpose}'")

        # Pull the specified font
        font = getattr(self, f"{font_purpose}font")

        # Get a dummy ImageDraw object
        from PIL import Image, ImageDraw
        test = Image.new('RGBA', (1,1))
        test_draw = ImageDraw.Draw(test, 'RGBA')

        # Check every char to see if it's the widest currently known
        consideration_set = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_='
        biggest_width = 0
        biggest_char = None
        for char in consideration_set:
            w, h = test_draw.textsize(text=char, font=font)
            if w > biggest_width:
                biggest_width = w
                biggest_char = char

        return biggest_char

    def set_font(self, purpose: str, size=None, typeface=None, RGBA=None):
        """Set the font for the specified purpose:
            `purpose` -> 'header', 'tract', 'sec', or 'lot'
            `size` -> int of font size
            `typeface` -> A string specifying which typeface to use,
            specified as any of:
            -- relative path (str) to a stock font (extension: .ttf)
                located in the `pyTRSplat/platsettings/` directory.
                    ex:  '_fonts/LiberationSans-Bold.ttf'
            -- absolute path (str) to a font (extension: .ttf) located
                anywhere.
            -- A key (str) to the Settings.TYPEFACES dict (which
                contains absolute paths to .ttf fonts)
                    ex:  'Sans-Serif (Bold)'
            `RGBA` -> 4-item tuple of RGBA color to use for the font
                (each element in the tuple must be an int 0 to 255).
            (Any unspecified parameters will remain unchanged for the
                specified `purpose`.)

            ex: settingsObj.set_font('header', size=112)
                    -> The header will be written with size 112 font,
                        using the same typeface as before.
            ex: settingsObj.set_font(
                    'header', typeface=r'C:/plats/fonts/customfont.ttf')
                    -> The header will be written with the typeface at
                        the specified filepath, using the same size as
                        before.
            (Or specify `size`, `typeface`, and/or `RGBA` at one time.)"""

        purpose = purpose.lower()

        # Confirm it's a legal font `purpose`
        Settings._font_purpose_error_check(purpose)

        # Check for errors in the specified `RGBA`, and then set it.
        if RGBA is not None:
            if not isinstance(RGBA, tuple):
                raise TypeError('`RGBA` must be tuple containing 4 ints from '
                                f'0 to 255. (Argument of type \'{type(RGBA)}\' '
                                'was passed)')
            elif len(RGBA) != 4:
                raise ValueError(f"`RGBA` must be tuple containing 4 ints from "
                                 f"0 to 255. "
                                 f"(Passed tuple contained {len(RGBA)} elements.")
            for val in RGBA:
                if not isinstance(val, int):
                    raise TypeError('`RGBA` must be tuple containing 4 ints '
                                    'from 0 to 255. (Passed tuple contained '
                                    f'element of type \'{type(val)}\')')
                if val < 0 or val > 255:
                    raise ValueError('`RGBA` must contain ints from 0 to 255. '
                                     f'(Passed tuple contained int {val})')
            # If it passes the checks, set it.
            setattr(self, f"{purpose}font_RGBA", RGBA)

        # If `typeface` and `size` are BOTH None, then the ImageFont
        # object won't change. So if we don't need to create a new
        # ImageFont obj, we can return now. (RGBA does not get encoded
        # in an ImageFont obj)
        if typeface is None and size is None:
            return

        if typeface is None:
            typeface = getattr(self, f"{purpose}font_typeface")

        if size is None:
            size = getattr(self, f"{purpose}font_size")

        # If typeface was passed as font name (i.e. Settings.TYPEFACES
        # key), set it to the corresponding absolute path now
        if typeface in Settings.TYPEFACES.keys():
            typeface = Settings.TYPEFACES[typeface]

        try:
            # Trying as though `typeface` is an absolute filepath
            self._create_set_font(purpose, size, typeface)
        except OSError as no_font_error:
            # If the user did not provide a valid (absolute) path to a
            # .ttf file, try it as a relative path to one of the fonts
            # in the stock `pyTRSplat\platsettings\_fonts\` dir
            candidate_abs_path = _rel_path_to_abs(typeface)
            if os.path.isfile(candidate_abs_path):
                typeface = candidate_abs_path
            else:
                # If it's also not a relative path, raise the original error
                raise no_font_error
            self._create_set_font(purpose, size, typeface)

        # We only want to change the respective typeface attribute AFTER
        # creating an ImageFont object, so that that has now had the
        # chance to raise any appropriate errors.
        setattr(self, f"{purpose}font_size", size)
        setattr(self, f"{purpose}font_typeface", typeface)

    @staticmethod
    def _font_purpose_error_check(purpose: str) -> bool:
        """Confirm the specified `purpose` is legal. If so, return
        `True`. Otherwise, raise a ValueError."""
        purposes = ['header', 'tract', 'sec', 'lot']
        if purpose not in purposes:
            raise ValueError(f"May customize font size and typeface for these "
                             f"purposes: {', '.join(purposes)}; "
                             f"Attempted to set font for purpose '{purpose}'")
        else:
            return True

    def _create_set_font(self, purpose: str, size: int, typeface: str):
        """Construct an ImageFont object from the specified `size` and
        `typeface` (a filepath to a .ttf file), and set it for the
        specified `purpose` (being 'header', 'tract', 'sec', or 'lot')."""

        purpose = purpose.lower()

        # Confirm it's a legal font `purpose`
        Settings._font_purpose_error_check(purpose)
        try:
            # Try as absolute path first
            fnt = ImageFont.truetype(typeface, size)
        except OSError as no_font_error:
            # If no good, try as relative path, within 'pyTRSplat/platsettings/'
            try:
                fnt = ImageFont.truetype(_rel_path_to_abs(typeface), size)
            except OSError:
                raise no_font_error
        setattr(self, f'{purpose}font', fnt)

    def _update_fonts(self):
        """Construct ImageFont objects from the current font settings,
        and set them to the appropriate attributes."""

        self._create_set_font('header', self.headerfont_size, self.headerfont_typeface)
        self._create_set_font('tract', self.tractfont_size, self.tractfont_typeface)
        self._create_set_font('sec', self.secfont_size, self.secfont_typeface)
        self._create_set_font('lot', self.lotfont_size, self.lotfont_typeface)

    @staticmethod
    def from_file(fp):
        """Compile and return a Settings object from .txt file at
        filepath `fp`."""

        setObj = Settings()
        setObj._import_file(fp)
        return setObj

    def _import_file(self, fp):
        """Read settings from a .txt file at filepath `fp` into this
        Settings object."""
        # Return codes:
        # 0 --> success
        # 1 --> Filename with extension other than `.txt` entered
        # 2 --> Could not open file at `filepath`

        if not fp.lower().endswith('.txt'):
            raise ValueError("Filename must end in '.txt'")

        with open(fp, 'r') as file:
            setting_lines = file.readlines()

        self._parse_text_to_settings(setting_lines)

    def _parse_text_to_settings(self, text):
        """
        INTERNAL USE:
        Parse appropriately formatted text into Settings attributes.

        :param text: Either a block of text (a string) of attribute data
        separated by linebreaks, or a list of already-separated
        attribute data (i.e. a list of strings).
        :return: Returns nothing, but sets the appropriate attributes to
        this Settings object.
        """
        setting_lines = text
        if isinstance(text, str):
            setting_lines = text.split('\n')

        for line in setting_lines:
            # Ignore data stored in angle brackets
            if len(line) == 0:
                continue
            if line[0] == '<':
                continue

            # For each line, parse the 'attrib=val' pair, and commit to
            # the setObj, using ._set_str_to_values()
            self._set_str_to_val(line.strip('\n'))

        # Remember to construct the font objects.
        self._update_fonts()

        # Success code:
        return 0

    def _set_str_to_val(self, attrib_val):
        """Take in a string of an attribute/value pair (in the format
        'attribute=value') and set the appropriate value of the
        attribute. (Expects the format generated by `.save_to_file()`
        method.)"""

        def try_2_4_tuple(text):
            """Check if the text represents a 2-item or 4-item tuple of ints.
            If so, return that tuple. If not, return None."""
            txt = text.replace(' ', '')
            txtlist = txt.split(',')

            # If len is neither 2 nor 4, we can rule out this attempt.
            if len(txtlist) not in [2, 4]:
                return None

            # If any element cannot be converted to an int, we can rule
            # out this attempt.
            tl_ints = []
            try:
                for txt in txtlist:
                    tl_ints.append(int(txt))
            except ValueError:
                return None

            # Success. This was a 2-item or 4-item tuple of ints
            return tuple(tl_ints)

        def try_int(text):
            """Check if the text represents an int. If so, return that int.
            If not, return None."""
            try:
                return int(text)
            except ValueError:
                return None

        def try_bool(text):
            """Convert string to its appropriate bool (i.e. 'True' -> True).
            Returns None if neither True nor False."""
            if text == 'True':
                return True
            elif text == 'False':
                return False
            else:
                return None

        # split attribute/value pair by '='
        components = attrib_val.split('=', maxsplit=1)

        # If only one component was found in the text, the input was
        # improperly formatted, and we return without setting anything.
        try:
            if components[1] == '':
                return None
        except IndexError:
            if len(components) == 1:
                return None

        att_name, val_text = components

        # If this is a string-type attribute (e.g., filepath to font
        # typefaces), set the val_text to the attribute, and return 0.
        if att_name in Settings.__stringTypeAtts__:
            setattr(self, att_name, val_text)
            return 0

        # Run each of our 'try' functions on `val_text` until we get a
        # hit, at which point, we set the converted value to the
        # att_name and return 0.
        for attempt in [try_2_4_tuple, try_int, try_bool]:
            val = attempt(val_text)
            if val is not None:
                setattr(self, att_name, val)
                return 0

        # If we haven't set our attribute/value by now, return error code -1
        return -1

    def save_to_file(self, filepath):
        """Output the data in this Settings object to .txt file at
        filepath `fp`."""
        # Returns 0 if success.

        if filepath[-4:].lower() != '.txt':
            raise ValueError("filename must end in '.txt'")

        # try:
        #     file = open(filepath, 'w')
        # except IOError:
        #     print(f'Could not open file: {filepath}.')
        #     return 2
        file = open(filepath, 'w')

        # These are the attributes we'll write to the file:
        attsToWrite = Settings.__setAtts__

        def attrib_text(att):
            """Get the output text for the attribute (`att`) from `self`"""
            val = getattr(self, att, None)
            if val is None:
                return ''

            if att in Settings.__typefaceAtts__:
                # Strip out the SETTINGS_DIR from the filepath of the
                # typefaces (leaving only the relative filepath to _fonts\)
                val.replace(Settings.SETTINGS_DIR + '\\', '')

            if isinstance(val, int):
                val = str(val)
            elif isinstance(val, (tuple, list)):
                # Convert each element of list/tuple to string; join w/ commas
                val_joiner = []
                for elem in val:
                    val_joiner.append(str(elem))
                val = ','.join(val_joiner)

            text = f"{att}={val}\n"

            return text

        for att in attsToWrite:
            file.write(attrib_text(att))

        file.close()
        return 0

    def _import_preset(self, name: str):
        """Load a saved preset into the current Settings object. The
        specified `name` must exist in the presets, which can be listed
        with `Settings.list_presets()`."""

        presets = Settings.list_presets()
        if name.lower() in presets:
            fp = f"{Settings.PRESET_DIRECTORY}\\{name}.txt"
            return self._import_file(fp)
        else:
            raise ValueError(
                f"'{name}' is not a saved Settings preset."
                f"\nCurrent presets directory: {Settings.PRESET_DIRECTORY}"
                f"\nCurrent presets: {', '. join(Settings.list_presets())}")

    @staticmethod
    def list_presets() -> list:
        """Return a sorted list of current presets in the preset directory
        (each returned as all lowercase)."""

        import os
        files = os.listdir(Settings.PRESET_DIRECTORY)
        presets = []
        for f in files:
            if f.lower().endswith('.txt'):
                presets.append(f.lower()[:-4])
        presets.sort()
        return presets

    def save_preset(self, name: str):
        """Save this Settings object as a preset (with the name first
        converted to all lowercase)."""

        fp = f"{Settings.PRESET_DIRECTORY}\\{name.lower()}.txt"
        self.save_to_file(fp)

    @staticmethod
    def _restore_default():
        """
        Restore the 'default' preset Setting object to the original,
        hard-coded default.
        """
        st = Settings(preset=None)
        st.save_preset('default')



def _abs_path_to_rel(fp: str):
    """
    INTERNAL USE:
    Convert an absolute path that points to a file or directory within
    this package, into a relative path -- i.e. relative to the
    'pyTRSplat/platsettings/' dir.

    If `fp` is already a relative filepath, or is an absolute filepath
    to a different directory, this will return the original `fp`.

    :param fp: Filepath to convert to relative filepath.
    :return: The filepath (str), relative to 'pyTRSplat/platsettings/'
    (i.e. relative to the directory for this package).
    """
    if fp.startswith(Settings.SETTINGS_DIR):
        fp.replace(Settings.SETTINGS_DIR + '\\', '')
    return fp


def _rel_path_to_abs(fp: str):
    """
    INTERNAL USE:
    Convert a relative path (a path within the `pyTRSplat/platsettings/'
    dir) to an absolute path, per the path of this package.
    :param fp: Relative filepath to convert to an absolute path.
    :return:
    """
    return f"{Settings.SETTINGS_DIR}\\{fp}"
