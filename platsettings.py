# Copyright (c) 2020, James P. Imes, all rights reserved.

from PIL import ImageFont

class Settings:
    """Configurable or default settings for drawing sections / townships
    and generating Plat objects.

    When a string is passed (as `preset=`) at init, it is assumed to be
    one of two things:
        -- the filepath to a saved .txt file of data that can be read
            into a Settings object, with the `._import_file()` method.
        -- the name of a saved preset (with no file extension), which
            will be loaded with the `._load_preset()` method.
    If neither of those is successful, a default Settings object will be
    initialized instead.

    A Settings object can be saved as a preset with the `.save_preset()`
    method (which will save as a .txt file in the `PRESET_DIRECTORY`).
    NOTE: File extension is NOT specified when saving/loading preset
        (the program handles that internally).

    A list of currently saved presets can be accessed by calling
    `Settings.list_presets()`.

    A Settings object can be saved to a (non-preset) .txt file at a
    specified filepath with the `.save_to_file()` method.
    NOTE: The file extension MUST BE SPECIFIED when saving/loading to a
        .txt file that is not a preset."""

    DEFAULT_TYPEFACE = r'assets/liberation-fonts-ttf-2.1.1/LiberationSans-Regular.ttf'
    PRESET_DIRECTORY = r'assets/presets/'

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

    # These are the attributes that will get included when outputting a
    # Settings object to text file (i.e. creating a preset).
    __setAtts__ = [
        'dim', 'headerfont_typeface', 'secfont_typeface', 'lotfont_typeface',
        'headerfont_size', 'tractfont_size', 'secfont_size', 'lotfont_size',
        'headerfont_RGBA', 'tractfont_RGBA', 'secfont_RGBA', 'lotfont_RGBA',
        'y_top_marg', 'y_bottom_marg', 'x_text_left_marg', 'x_text_right_marg',
        'y_px_before_tracts', 'y_px_between_tracts', 'qq_side',
        'sec_line_stroke', 'ql_stroke', 'qql_stroke', 'sec_line_RGBA',
        'ql_RGBA', 'qql_RGBA', 'qq_fill_RGBA', 'centerbox_wh',
        'lot_num_offset_px', 'write_header', 'write_tracts',
        'write_section_numbers', 'write_lot_numbers'
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
                    Settings.__restore_default()
            except:
                preset = None

        # Dimensions of the image.
        self.dim = Settings.LETTER_200ppi

        # Font typeface, size, and RGBA values
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

        # Default font objects will be replaced shortly.
        self.headerfont = ImageFont.truetype(Settings.DEFAULT_TYPEFACE)
        self.tractfont = ImageFont.truetype(Settings.DEFAULT_TYPEFACE)
        self.secfont = ImageFont.truetype(Settings.DEFAULT_TYPEFACE)
        self.lotfont = ImageFont.truetype(Settings.DEFAULT_TYPEFACE)

        # Construct ImageFont objects from the above settings:
        self._update_fonts()

        # Distance between top of image and top of first row of sections.
        self.y_top_marg = 180

        # Distance between top section line and the T&R written above it.
        self.y_header_marg = 15

        # Bottom margin before triggering 'panic' button.
        self.y_bottom_marg = 80

        # px indent for tract text (from the left side of the image).
        self.x_text_left_marg = 100
        # TODO: Set x_text_left_marg for various presets.

        # px for tract text right margin (distance from right side of image
        # that we can write up to).
        self.x_text_right_marg = 0
        # TODO: Set x_text_right_marg for various presets.

        # Distance between bottom section line and the first tract text written.
        self.y_px_before_tracts = 40

        # Distance between tracts.
        self.y_px_between_tracts = 10
        # TODO: Set y_px_between_tracts for various presets.

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

        # If `preset` is specified as a string, we assume it is a preset
        # and attempt to load it as Settings data.
        if isinstance(preset, str):
            self._import_preset(preset)

    def set_font(self, purpose: str, typeface: str, size: int):
        """Set the font for the specified purpose:
            `purpose` -> 'header', 'tract', 'sec', or 'lot'
            `typeface` -> filepath (str) to a font (extension: .ttf)
            `size` -> int of font size
        (Constructs a PIL.ImageFont object and sets it to the
        appropriate attribute.)"""

        if purpose.lower() not in ['header', 'tract', 'sec', 'lot']:
            # Failure.
            return -1

        fnt = ImageFont.truetype(typeface, size)
        setattr(self, f"{purpose.lower()}font", fnt)

    def _update_fonts(self):
        """Construct ImageFont objects from the current font settings,
        and set them to the appropriate attributes."""
        self.set_font('header', self.headerfont_typeface, self.headerfont_size)
        self.set_font('tract', self.tractfont_typeface, self.tractfont_size)
        self.set_font('sec', self.secfont_typeface, self.secfont_size)
        self.set_font('lot', self.lotfont_typeface, self.lotfont_size)

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
            settingLines = file.readlines()

        for line in settingLines:
            # Ignore data stored in angle brackets
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
            fp = f"{Settings.PRESET_DIRECTORY}{name}.txt"
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

        fp = f"{Settings.PRESET_DIRECTORY}{name.lower()}.txt"
        self.save_to_file(fp)

    @staticmethod
    def __restore_default():
        """Restore the 'default' preset Setting object to the original,
        hard-coded default."""
        st = Settings(preset=None)
        st.save_preset('default')
