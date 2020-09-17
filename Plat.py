# Copyright (c) 2020, James P. Imes. All rights reserved.

"""
pyTRSplat -- A module to generate land plat images of full townships
(6x6 grid) or single sections from PLSS land descriptions ('legal
descriptions'), using the pyTRS parsing module.
"""

# TODO: Give the option to depict `.unhandled_lots` on plats somewhere.
#  i.e. warn users that certain lots were not incorporated onto the plat

# TODO: Consider making TextBox its own class.

from pathlib import Path

# Submodules from this project.
from Grid import TownshipGrid, SectionGrid, LotDefinitions, TwpLotDefinitions, LotDefDB
from Grid import plssdesc_to_grids, filter_tracts_by_twprge, confirm_file_ext
from PlatSettings import Settings
from PlatQueue import PlatQueue, MultiPlatQueue

# For drawing the plat images, and coloring / writing on them.
from PIL import Image, ImageDraw, ImageFont

# For parsing text of PLSS land descriptions into its component parts.
from pyTRS.pyTRS import PLSSDesc, Tract
from pyTRS.pyTRS import decompile_twprge, break_trs
from pyTRS import version as pyTRS_version

import _constants

__version__ = _constants.__version__
__versionDate__ = _constants.__versionDate__
__author__ = _constants.__author__
__email__ = _constants.__email__


def version():
    """Return the current version and version date as a string."""
    return f'v{__version__} - {__versionDate__}'


class Plat:
    """An object containing an PIL.Image object of a 36-section (in
    `.image`), as well as various attributes for platting on top of it.
    Notably, `.sec_coords` is a dict of the pixel coordinates for the
    NWNW corner of each of the 36 sections (keyed by integers 1 - 36,
    inclusive).

    NOTE: We can plat a single section, with `only_section=<int>` at
    init, in which case, `.sec_coords` will have only a single key. (Be
    sure to choose settings that are appropriate for a single-section
    plat.)

    Plat objects can process these types of objects:
        pyTRS.Tract**, SectionGrid, TownshipGrid
    (**pyTRS.Tract objects are imported in this module as `Tract`.)

    At init, configure the look, size, fonts, etc. of the Plat by
    passing a Settings object to `settings=`. (Can also pass the name of
    a preset -- see Settings docs for more details.)

    For better results, optionally pass a TwpLotDefinition (or 'tld' for
    short) to `tld=` at init, to specify which lots correspond with
    which QQ in each respective section. (See more info in
    `grid.TwpLotDefinition` docs and `grid.LotDefDB` docs.)
    # TODO: :param: allow_ld_defaults

    """

    # TODO: Wherever TLD or LD is referenced in a kwarg, allow it
    #   to pull from self.tld or self.ld.

    def __init__(self, twp='', rge='', only_section=None, settings=None,
                 tld=None, allow_ld_defaults=False):
        self.twp = twp
        self.rge = rge
        self.twprge = twp + rge

        # NOTE: settings can be specified as a Settings object, or by
        # passing the name of an already saved preset (as a string).
        # Alternatively, to load settings data from a DIFFERENT source
        # (i.e. a '.txt' file saved somewhere OTHER than the presets
        # directory), first use the `Settings.from_file()` method, or
        # something like:
        #      `... settings=Settings.from_file(<whatever filepath>)...`
        if isinstance(settings, str):
            settings = Settings(preset=settings)

        # If settings was not specified, create a default Settings object.
        if settings is None:
            settings = Settings()
        elif isinstance(settings, str):
            # If passed as a string, it may be a preset or filepath to a
            # file that can be imported as a Settings object. Create
            # that Settings object now. (If that fails, it will be a
            # defualt Settings object anyway.)
            settings = Settings(settings)
        self.settings = settings

        # The main Image of the plat, and an ImageDraw object for it.
        self.image = Image.new('RGBA', settings.dim, Settings.RGBA_WHITE)
        self.draw = ImageDraw.Draw(self.image, 'RGBA')

        # Overlay on which we'll plat QQ's, and an ImageDraw object for it
        self.overlay = Image.new('RGBA', settings.dim, (255, 255, 255, 0))
        self.overlay_draw = ImageDraw.Draw(self.overlay, 'RGBA')

        # A dict of the sections and the (x,y) coords of their NWNW corner:
        self.sec_coords = {}

        # Draw the standard 36 sections, or the `only_section` (an int).
        # (If `only_section` is None, then will draw all 36 in 6x6 grid.
        # If specified, will draw only that section.)
        self._draw_all_sections(only_section=only_section)
        self.header = self._gen_header(only_section=only_section)

        if self.settings.write_header:
            self._write_header()

        # Text box for writing tract info (or other custom text)
        self.text_box = None
        self.text_draw = None
        self.text_box_exists = False
        self.text_box_exhausted = True
        self.next_line_is_last_line = False
        self.text_line_width = None
        # Create the text_box (if possible with the provided settings)
        # NOTE: `.text_box` and `.text_draw` may remain None!
        self.new_textbox()
        self.deduce_chars_per_line()

        # Keeping track of the current position where text (e.g., tracts
        # etc.) can be written -- i.e. where we've written up to, and
        # where we can still write at in x,y pixel coordinates.
        # IMPORTANT: These coords refer to position within the
        # `.text_box` -- NOT within `.image`.
        self.text_cursor = self.reset_cursor()
        # NOTE: Other cursors can also be created
        #   ex: This would create a new cursor at (0, 0) and accessed as
        #       `platObj.highlighter`:
        #           >>> platObj.reset_cursor(cursor='highlighter')
        #   ex: This would create a new cursor at the specified x,y
        #       coords (120,180) and accessed as `platObj.underliner`:
        #           >>> platObj.set_cursor(120, 180, cursor='underliner')

        # A PlatQueue object holding elements/tracts that will be platted.
        self.pq = PlatQueue()

        # LotDefinitions and/or TwpLotDefinitions, in case we want to
        # call `.plat_tract()`.  The appropriate one will be set
        # shortly, depending on whether `only_section` was specified
        # (LD's apply to single sections, whereas TLD's apply to whole
        # townships).
        self.ld = None
        self.tld = None

        # If a LotDefDB object was passed instead of a TLD or LD object,
        # get the appropriate TLD from it (per twp+rge key); and if none
        # exists, then use the init-specified `allow_ld_defaults` to
        # determine whether to get a default TLD object, or an empty TLD
        # object.  Also then get the LD from it if `only_section` was
        # init-specified; and if no LD exists, also rely on
        # `allow_ld_defaults` to determine whether we get back a default
        # LD object, or an empty LD object.
        # (`force_tld_return=True` and `force_ld_return=True` ensure
        # that the returned objects are not None, but will be at least
        # an empty version of the respective TLD and LD objects.)
        if isinstance(tld, LotDefDB):
            tld = tld.get_tld(
                twp + rge, allow_ld_defaults=allow_ld_defaults,
                force_tld_return=True)
            if only_section is not None:
                ld = tld.get_ld(
                    only_section, allow_ld_defaults=allow_ld_defaults,
                    force_ld_return=True)
            else:
                ld = None
        elif isinstance(tld, LotDefinitions):
            ld = tld
            tld = None
        elif isinstance(tld, TwpLotDefinitions):
            ld = None
        else:
            # Fall back on default LD and TLD objects.
            ld = LotDefinitions()
            tld = TwpLotDefinitions()

        # And finally set the appropriate ld or tld.
        if only_section is not None:
            self.ld = ld
        else:
            self.tld = tld

        # Whether or not to pull default TLD's (and LD's) when undefined
        self.allow_ld_defaults = allow_ld_defaults

    @staticmethod
    def from_twprge(
            twprge='', only_section=None, settings=None, tld=None,
            allow_ld_defaults=False):
        """Generate an empty Plat object by specifying twprge as a single
        string, rather than as twp and rge separately."""
        twp, rge, _ = break_trs(twprge)

        return Plat(
            twp=twp, rge=rge, only_section=only_section, settings=settings,
            tld=tld, allow_ld_defaults=allow_ld_defaults)

    @staticmethod
    def from_queue(
            pq, twp='', rge='', only_section=None, settings=None, tld=None,
            allow_ld_defaults=False):
        """Generate and return a filled-in Plat object from a PlatQueue
        object."""
        sp_obj = Plat(
            twp=twp, rge=rge, only_section=only_section, settings=settings,
            tld=tld, allow_ld_defaults=allow_ld_defaults)
        sp_obj.process_queue(pq)
        return sp_obj

    def queue(self, plattable, tracts=None):
        """Queue up an object for platting -- i.e. pass through the
        arguments to the `.queue()` method in the Plat's PlatQueue
        object."""
        self.pq.queue(plattable, tracts)

    def process_queue(self, queue=None, allow_ld_defaults=None):
        """Process all objects in a PlatQueue object. If `queue=None`,
        the PlatQueue object that will be processed is the one stored in
        this Plat's `.pq` attribute."""

        if allow_ld_defaults is None:
            allow_ld_defaults = self.allow_ld_defaults

        # If a different PlatQueue isn't otherwise specified, use the
        # Plat's own `.pq` from init.
        if queue is None:
            queue = self.pq

        for itm in queue:
            if not isinstance(itm, PlatQueue.SINGLE_PLATTABLES):
                raise TypeError(f"Cannot process type in PlatQueue: "
                                f"{type(itm)}")
            if isinstance(itm, SectionGrid):
                self.plat_section_grid(itm)
            elif isinstance(itm, TownshipGrid):
                self.plat_township_grid(itm)
            elif isinstance(itm, Tract):
                self.plat_tract(itm, write_tract=False,
                                allow_ld_defaults=allow_ld_defaults)

        if self.settings.write_tracts:
            self.write_all_tracts(queue.tracts)

    def _gen_header(self, only_section=None):
        """Generate the text of a header containing the T&R and/or
        Section number."""

        twp = str(self.twp)
        rge = str(self.rge)
        NS = 'undefined'
        EW = 'undefined'

        # Check that directions for twp and rge were appropriately specified.
        # If no direction was specified, then also check if (only) digits were
        # specified for twp and rge. If that's the case, arbitrarily assign 'n'
        # and 'w' as their directions (only for purposes of `decompile_twprge()`
        # -- will be cut off before the header itself is compiled).
        if not twp.lower().endswith(('n', 's')):

            if twp != '':
                try:
                    twp = str(int(twp))
                    twp = twp + 'n'
                except ValueError:
                    pass
        if not rge.lower().endswith(('e', 'w')):
            EW = 'undefined'
            if rge != '':
                try:
                    rge = str(int(rge))
                    rge = rge + 'w'
                except ValueError:
                    pass

        twpNum, try_NS, rgeNum, try_EW = decompile_twprge(twp + rge)

        if try_NS == 'n':
            NS = 'North'
        elif try_NS == 's':
            NS = 'South'

        if try_EW == 'e':
            EW = 'East'
        elif try_EW == 'w':
            EW = 'West'

        if twp + rge == '':
            # If neither twp nor rge have been set, we will not write T&R in header.
            twptxt = ''
        elif 'TRerr' in [twpNum, rgeNum]:
            # If N/S or E/W were not specified, or if there's some other T&R error
            twptxt = '{Township/Range Error}'
        else:
            twptxt = f'Township {twpNum} {NS}, Range {rgeNum} {EW}'

        if only_section is not None:
            # If we're platting a single section.
            return f"{twptxt}{', ' * (len(twptxt) > 0)}Section {only_section}"
        else:
            return twptxt

    def _draw_all_sections(self, only_section=None):
        """Draw the 36 sections in the standard 6x6 grid; or draw a
        single section if `only_section=<int>` is specified."""

        # Saving some line space shortly by setting this variable:
        settings = self.settings

        w, h = settings.dim

        # Our township (a square) will either be a 6x6 grid of sections,
        # or a single section (i.e. 1x1).
        sections_per_side = 6
        if only_section is not None:
            sections_per_side = 1

        # Number of QQ divisions per section -- i.e. a 4x4 grid of QQ's,
        # or a square of 4 units (QQ's) by 4 units.
        qqs_per_sec_side = 4

        # Multiplying `settings.qq_side` (an int representing how long
        # we draw a QQ side) by `qq_per_sec_side` (an int representing
        # how many QQ's per section side) gets us the number of px per
        # section side.
        section_length = settings.qq_side * qqs_per_sec_side

        # We'll horizontally center our plat on the page. (4 is the number
        # of QQ's drawn per section)
        x_start = (w - (section_length * sections_per_side)) // 2

        # The plat will start this many px below the top of the page.
        y_start = settings.y_top_marg

        # PLSS sections "snake" from the NE corner of the township west
        # then down, then they cut back east, then down and west again,
        # etc., thus:
        #           6   5   4   3   2   1
        #           7   8   9   10  11  12
        #           18  17  16  15  14  13
        #           19  20  21  22  23  24
        #           30  29  28  27  26  25
        #           31  32  33  34  35  36
        #
        # ...so accounting for this is a little trickier:
        sec_nums = list(range(6, 0, -1))
        sec_nums.extend(list(range(7, 13)))
        sec_nums.extend(list(range(18, 12, -1)))
        sec_nums.extend(list(range(19, 25)))
        sec_nums.extend(list(range(30, 24, -1)))
        sec_nums.extend(list(range(31, 37)))

        # If drawing only one section, override that list with a
        # single-element list.
        if only_section is not None:
            sec_nums = [int(only_section)]

        # Generate section(s) on the plat, and number them.
        #
        # For each section, we start at (x_start, y_start) and move
        # `j` section-lengths over, and `i` section-lengths down,
        # at which point we are at the NW corner of the section,
        # from which we'll draw our 4x4 grid for that section and
        # mark the coord in the `.sec_coords` dict.
        #
        # Remember that sections_per_side is `1` if we're platting only
        # a single section, in which case i and j will only be 0.
        for i in range(sections_per_side):
            for j in range(sections_per_side):
                sec_num = sec_nums.pop(0)
                cur_x = x_start + section_length * j
                cur_y = y_start + section_length * i
                self._draw_sec((cur_x, cur_y), section=sec_num)
                self.sec_coords[sec_num] = (cur_x, cur_y)

    def _write_header(self, text=None):
        """Write the header at the top of the page."""

        if text is None:
            text = self.header

        W = self.image.width
        w, h = self.draw.textsize(text, font=self.settings.headerfont)

        # Center horizontally and write `settings.y_header_marg` px above top section
        text_x = (W - w) / 2
        text_y = self.settings.y_top_marg - h - self.settings.y_header_marg
        self.draw.text(
            (text_x, text_y),
            text,
            font=self.settings.headerfont,
            fill=self.settings.headerfont_RGBA)

    def new_textbox(self):
        """Create a textbox Image per the Plat's settings."""

        x0, y0 = self.first_text_xy()
        # Bottom / right-most available x and y
        y1 = self.settings.dim[1] - self.settings.y_bottom_marg
        x1 = self.settings.dim[0] - self.settings.x_text_right_marg

        if x0 >= x1 or y0 >= y1:
            self.text_box = None
            self.text_draw = None
            self.text_box_exists = False
        else:
            self.text_box = Image.new(
                'RGBA', (x1 - x0, y1 - y0), Settings.RGBA_WHITE)
            self.text_draw = ImageDraw.Draw(self.text_box, 'RGBA')
            self.text_box_exists = True
            self.text_box_exhausted = False

    def first_text_xy(self, settings=None):
        """Get the top/left-most pixel available for writing text (i.e.
        top/left corner of where we can create and place a textbox), per
        Plat settings."""

        if settings is None:
            settings = self.settings

        # Number of QQ divisions per section -- i.e. a 4x4 grid of QQ's,
        # or a square of 4 units (QQ's) by 4 units.
        qqs_per_sec_side = 4

        # Multiplying `settings.qq_side` (an int representing how long
        # we draw a QQ side) by `qq_per_sec_side` (an int representing
        # how many QQ's per section side) gets us the number of px per
        # section side.
        sec_len = settings.qq_side * qqs_per_sec_side

        # If we platted all 36 sections, there are 6 per side (6x6 grid)
        secs_per_twp_side = 6
        if len(self.sec_coords.keys()) == 1:
            # But if we only platted one, it's a 1x1 grid.
            secs_per_twp_side = 1

        # First available x (i.e. the left margin)
        x0 = settings.x_text_left_marg

        # First available y below the plat...
        #   Starting at the top of the image, move down to the top of
        #   the plat itself...
        y0 = settings.y_top_marg
        #   Then go to the bottom of the plat...
        y0 += sec_len * secs_per_twp_side
        #   And then finally add the settings-specified buffer between
        #   the plat and the first line of text
        y0 += settings.y_px_before_tracts

        return (x0, y0)

    def deduce_chars_per_line(
            self, commit=True, harder_limit=False, w_limit=None):
        """
        Deduce (roughly) how many characters we can allow to be written
        in a single line, using the current `tractfont` in settings.

        :param commit: Save the deduced max line-length to
        `self.text_line_width`
        :type commit: bool
        :param w_limit: Provide a custom width limit (in px) to check
        against. If not specified, we will check against the width of
        `self.text_box` (if it exists). Will result in shorter lines
        written, but less likely to encroach on margins.
        :type w_limit: int
        :param harder_limit: Will check how many of a 'wider' character
        can fit in a single line. (False by default.)
        :type harder_limit: bool
        """

        # If we have no text_box, and the user hasn't provided a custom
        # `w_limit`, then return None.
        if not self.text_box_exists and w_limit is None:
            if commit:
                self.text_line_width = None
            return None
        font = self.settings.tractfont

        if w_limit is None:
            w_limit = self.text_box.width
        base = 'The Quick Brown Fox Jumps Over The Lazy Dog'
        if harder_limit:
            # If using `harder_limit`, will take the widest known
            # character in the font and only check how many of those
            # will fit in a line within our textbox.
            base = self.settings.deduce_biggest_char(font_purpose='tract')
        test = base[0]
        num_chars = 1
        while True:
            # Add the next char from base to test (and wrap around).
            test = test + base[num_chars % len(base)]
            w, h = self.text_draw.textsize(text=test, font=font)

            # Check if we've gone past the width of our textbox
            if w > w_limit:
                break
            else:
                num_chars += 1

        if commit:
            self.text_line_width = num_chars
        return num_chars

    def reset_cursor(self, cursor='text_cursor') -> tuple:
        """
        Set the specified cursor (defaults to 'text_cursor') to (0, 0).
        NOTE: Cursor coords refer to `.text_box` image, not to `.image`!

        :param cursor: The name of the cursor to be set to (0, 0).
        The named cursor will be stored as a Plat object attribute.
        Specifically, if a string is NOT passed as `cursor=`, the
        stored coord will be set to the default `.text_cursor`. However,
        if the particular cursor IS specified, it will save the
        resulting coord to that attribute name.
        Be careful not to overwrite other required attributes.
        :return: (0, 0)
        :Example:

        ex: 'setObj.reset_cursor()  # The default
            -> setObj.text_cursor == (0, 0)
            -> and returns (0, 0)
        ex: 'setObj.reset_cursor(cursor='highlight')
            -> setObj.highlight == (0, 0)
            -> and returns (0, 0)
        """

        self.set_cursor((0, 0), cursor)
        return (0, 0)

    def set_cursor(self, coord, cursor='text_cursor'):
        """Set the cursor to the specified x and y coords. If a string
        is NOT passed as `cursor=`, the committed coord will be set to
        the default `.text_cursor`. However, if the particular cursor
        IS specified, it will save the resulting coord to that attribute
        name.
            ex: 'setObj.set_cursor((200, 1200))
                -> setObj.text_cursor == (200, 1200)
            ex: 'setObj.set_cursor((200, 1200), cursor='highlight')
                -> setObj.highlight == (200, 1200)
        Be careful not to overwrite other required attributes."""

        setattr(self, cursor, coord)

    # def same_line_cursor(
    #         self, xy_delta: tuple, cursor='text_cursor', commit=True,
    #         additional_x_px=0, left_margin=None, additional_indent=0) -> tuple:
    #     """Move the specified `cursor` to the right, on the same so-called
    #     'line', after having written some text at that cursor.
    #     `xy_delta` should be a tuple of (width, height) of text that was
    #     written. It will move the cursor right that many px (plus the
    #     optionally specified `additional_x_px` -- e.g., px for an
    #     additional space character). Returns the resulting coord.
    #
    #     If the resulting cursor coord would be illegal (per settings),
    #     it will move down to a 'new line'. The parameters `left_margin`
    #     and `additional_indent` have no effect unless we end up moving
    #     the cursor to the next line (in which case, they have the same
    #     effect as they do in the `.next_line_cursor()` method).
    #
    #     If a string is NOT passed as `cursor=`, the returned (and
    #     optionally committed) coord will be set to the default
    #     `.text_cursor`. However, if the particular cursor IS specified,
    #     it will save the resulting coord to that attribute name (so long
    #     as `commit=True`).
    #
    #     Further, if the cursor is specified but does not yet exist, this
    #     will read from `.text_cursor` (to calculate the updated coord)
    #     but save to the specified cursor.
    #
    #     Be careful not to overwrite other required attributes."""
    #
    #     # Discard the y from xy_delta, but get the x_delta.
    #     x_delta, _ = xy_delta
    #
    #     # Get the x0 and y0 from the cursor.  (Using nested `getattr`
    #     # calls ensures we get `.text_cursor`, if `cursor=` was
    #     # specified as a string that wasn't already set; but this won't
    #     # overwrite the specified `cursor` for committing the coord
    #     # shortly.)
    #     x0, y0 = getattr(self, cursor, getattr(self, 'text_cursor'))
    #
    #     y = y0
    #
    #     total_x_delta = x_delta + additional_x_px
    #
    #     # Make sure that the resulting candidate cursor movement is legal.
    #     # If not, we'll set the coord to the next line instead, by passing
    #     # through our arguments to `.next_line_cursor()`.
    #     if self._check_legal_cursor((total_x_delta, 0), cursor):
    #         coord = (x0 + total_x_delta, y)
    #     else:
    #         coord = self.next_line_cursor(
    #             xy_delta=xy_delta, cursor=cursor, commit=False,
    #             left_margin=left_margin, additional_indent=additional_indent)
    #
    #     if commit:
    #         self.set_cursor(coord, cursor=cursor)
    #     return coord

    def next_line_cursor(
            self, xy_delta: tuple, cursor='text_cursor', commit=True,
            left_margin=None, additional_indent=0) -> tuple:
        """
        Move the specified `cursor` to the so-called 'next line', after
        having written some text at that cursor.

        :param xy_delta: A 2-tuple of (width, height) of text that was
        just written.
        IMPORTANT: Assumes a single line of text was written!
        :param cursor:
        If a string is NOT passed as `cursor=`, the returned (and
        optionally committed) coord will be set to the default
        `.text_cursor`. However, if the particular cursor IS specified,
        it will save the resulting coord to that attribute name (so long
        as `commit=True`).
        NOTE: If the cursor is specified but does not yet exist, this
        will read from `.text_cursor` (to calculate the updated coord)
        but save to the specified cursor.
        Be careful not to overwrite other required attributes!
        :param commit: A bool, whether to store the calculated coord to
        the specified cursor.
        :param left_margin: How many additional px to indent from the
        left margin. (Will default to settings, if not specified here.)
        :param additional_indent: How many px to indent IN ADDITION TO
        the left_margin.
        :return: Returns the resulting coord.
        """

        # If `left_margin` is not specified (as an int), set it to the
        # x-value of the original cursor position (discard the y value).
        if not isinstance(left_margin, int):
            left_margin = 0

        # Set x to the left_margin (plus optional indent).
        x = left_margin + additional_indent

        # Discard the x from xy_delta, but get the y_delta.
        _, y_delta = xy_delta

        # Discard the x0 from the cursor, but get y0.  (Nested `getattr`
        # calls ensures we get `.text_cursor`, if `cursor=` was
        # specified as a string that wasn't already set; but this won't
        # overwrite the specified `cursor` for committing the coord
        # shortly.)
        _, y0 = getattr(self, cursor, getattr(self, 'text_cursor'))

        # We will add to our y-value the px between tracts, per settings.
        y_line_spacer = self.settings.y_px_between_tracts

        coord = (x, y0 + y_delta + y_line_spacer)

        # If two lines from now would be illegal, we deduce that the
        # next line will be the last legal.
        two_lines_later_legal = self._check_legal_cursor(
            (0, y_delta * 3 + y_line_spacer * 2), cursor=cursor)

        # But if the next line is already illegal, then the one just
        # written one is the last line.
        one_line_later_legal = self._check_legal_cursor(
            (0, y_delta * 2 + y_line_spacer), cursor=cursor)

        if commit:
            self.set_cursor(coord, cursor=cursor)
            if not one_line_later_legal:
                self.text_box_exhausted = True
            if one_line_later_legal and not two_lines_later_legal:
                self.next_line_is_last_line = True
            else:
                self.next_line_is_last_line = False

        return coord

    def update_cursor(
            self, xy_delta, cursor='text_cursor', commit=True) -> tuple:
        """
        Update the coord of the cursor, by adding the `x_delta` and
        `y_delta` to the current coord of the specified `cursor`.

        :param xy_delta: A tuple of (x, y) values, being how far (in px)
        the cursor has traveled from its currently set coord.
        :param cursor: The name of the cursor being updated. (Defaults
        to 'text_cursor'.)
        If a string is NOT passed as `cursor=`, the committed coord will
        be set to the default `.text_cursor`. However, if the particular
        cursor IS specified, it will save the resulting coord to that
        attribute name (so long as `commit=True`).

        Further, if the cursor is specified but does not yet exist, this
        will read from `.text_cursor` (to calculate the updated coord)
        but save to the specified cursor.
        Be careful not to overwrite other required attributes.
        :param commit: Whether to store the new coord to the cursor
        attribute in `self`.
        :return: Returns the updated coord, and optionally stores it to the
        cursor attribute with `commit=True` (on by default).
        """

        if self.text_box is None:
            return None

        # Pull the specified cursor. If it does not already exist as an
        # attribute in this object, it will fall back to `.text_cursor`,
        # which exists for every Settings object, per init.
        x_delta, y_delta = xy_delta
        x0, y0 = getattr(self, cursor, getattr(self, 'text_cursor'))
        coord = (x0 + x_delta, y0 + y_delta)

        # Only if `commit=True` do we set this.
        if commit:
            setattr(self, cursor, coord)

        return coord

    def _check_legal_textwrite(self, text, font, cursor='text_cursor') -> bool:
        """
        Check if there is enough room to write the specified text,
        using the specified font within the textbox in `self.text_box`.

        :param text: The text to check.
        :param font: The font that will be used to write the text.
        :type font: ImageFont
        :param cursor: The name of the cursor at which the text will be
        written. (Defaults to 'text_cursor')
        :return: A bool, whether or not the text can be written within
        the margins.
        """

        if self.text_box is None:
            return False

        w, h = self.text_draw.textsize(text, font=font)

        # Only `legal` matters for this method.
        legal = self._check_legal_cursor((w, h), cursor=cursor)
        return legal

    def _check_cursor_overshoot(
            self, xy_delta: tuple, cursor='text_cursor') -> tuple:
        """
        Check how many px the cursor has gone beyond right and bottom
        edges of the textbox in `self.text_box`. (Assumes that it is
        starting from a legal coord.)

        :param xy_delta: A tuple of (x, y) values, being how far (in px)
        the cursor has traveled from its currently set coord.
        :param cursor: The name of the cursor being checked. (Defaults
        to 'text_cursor'.)
        :return: Returns an (x, y) tuple of how many px past the margins
        the cursor has gone. (Negative numbers mean that it is within
        the right/bottom margins, but is agnostic as to the top/left
        margins.) NOTE: Returns None if `self.text_box` is None.
        """

        if self.text_box is None:
            return None

        # Confirm `cursor` points to an existing tuple in self's
        # attributes. If not, we'll use the `.text_cursor` attribute.
        cursor_check = getattr(self, cursor, None)
        if not isinstance(cursor_check, tuple):
            cursor = 'text_cursor'

        # Get the hypothetical resulting cursor location if xy_delta is
        # applied. (`commit=False` means it won't be stored yet.)
        x, y = self.update_cursor(xy_delta, cursor, commit=False)

        x_overshot = x - self.text_box.width
        y_overshot = y - self.text_box.height

        return (x_overshot, y_overshot)

    def _check_legal_cursor(
            self, xy_delta: tuple, cursor='text_cursor') -> bool:
        """
        Check if there is enough room to move the cursor from its
        current position by `xy_delta` (a tuple of x,y value) before
        going outside the dimensions of the textbox in `self.text_box`.
        (Assumes that it is starting from a legal coord.)

        :param xy_delta: A tuple of (x, y) values, being how far (in px)
        the cursor has traveled from its currently set coord.
        :param cursor: The name of the cursor at which the text will be
        written. (Defaults to 'text_cursor')
        :return: A bool, whether or not the resulting coord will be
        within the margins.
        """

        if self.text_box is None:
            return False

        x_overshot, y_overshot = self._check_cursor_overshoot(xy_delta, cursor)

        legal = True
        if x_overshot > 0 or y_overshot > 0:
            legal = False

        return legal

    def output(self, filepath=None):
        """Merge the drawn overlay (i.e. filled QQ's) onto the base
        township plat image and return an Image object. Optionally save
        the image to file if `filepath=<filepath>` is specified."""
        merged = Image.alpha_composite(self.image, self.overlay)

        if self.text_box is not None:
            merged.paste(self.text_box, self.first_text_xy())

        # TODO: Add the option with *args to specify which layers get
        #   included in the output. That also will require me to have
        #   separate layers for QQ's, the grid, labels, etc.
        #   And that, in turn, will require me to change methods to
        #   /plat/ onto multiple layers.

        if filepath is not None:
            merged.save(filepath)

        return merged

    def show(self):
        """Flatten and display the plat Image."""
        self.output().show()

    def plat_section_grid(self, secGrid: SectionGrid, qq_fill_RGBA=None):
        """Project a SectionGrid object onto an existing Plat Object
        (i.e. fill in any QQ hits per the `SectionGrid.QQgrid` values)."""
        secNum = int(secGrid.sec)
        for coord in secGrid.filled_coords():
            self.fill_qq(secNum, coord, qq_fill_RGBA=qq_fill_RGBA)
        if self.settings.write_lot_numbers:
            self.write_lots(secGrid)

    @staticmethod
    def from_section_grid(secGrid: SectionGrid, tracts=None, settings=None):
        """Return a section-only Plat object generated from a
        SectionGrid object."""
        platObj = Plat(
            twp=secGrid.twp,
            rge=secGrid.rge,
            settings=settings,
            only_section=secGrid.sec)
        platObj.plat_section_grid(secGrid)
        if platObj.settings.write_tracts:
            platObj.write_all_tracts(tracts)
        return platObj

    @staticmethod
    def from_township_grid(twpGrid, tracts=None, settings=None):
        """Return a Plat object generated from a TownshipGrid object."""
        twp = twpGrid.twp
        rge = twpGrid.rge
        platObj = Plat(twp=twp, rge=rge, settings=settings)
        platObj.plat_township_grid(twpGrid=twpGrid, tracts=tracts)
        return platObj

    def plat_township_grid(self, twpGrid, tracts=None):
        """Project a TownshipGrid object onto an existing Plat object."""

        # Generate the list of sections that have anything in them.
        # We use `include_pinged=True` to also include any sections
        # that were 'pinged' by a setter method, but may not have had
        # any values actually set (e.g., perhaps for a Tract object that
        # failed to generate any lots/QQ's when parsed by pyTRS).
        sec_list = twpGrid.filled_sections(include_pinged=True)

        # Plat each Section's filled QQ's onto our new overlay.
        for sec in sec_list:
            if self.settings.write_lot_numbers:
                # If so configured in settings, write lot numbers onto QQ's
                self.write_lots(sec)
            self.plat_section_grid(sec)

        # Write the Tract data to the bottom of the plat (or not, per settings).
        if self.settings.write_tracts:
            self.write_all_tracts(tracts)

        return self.output()

    @staticmethod
    def from_tract(
            tractObj, settings=None, single_sec=False, ld=None,
            allow_ld_defaults=False):
        """Return a Plat object generated from a Tract object. Specify
        `single_sec=True` to plat only one section, or `False` (the
        default) to show the entire township."""
        twp = tractObj.twp
        rge = tractObj.rge
        sec = tractObj.sec
        only_sec = None
        if single_sec:
            only_sec = str(int(sec))

        platObj = Plat(
            twp=twp, rge=rge, settings=settings, only_section=only_sec,
            allow_ld_defaults=allow_ld_defaults)
        platObj.plat_tract(tractObj, ld=ld)
        return platObj

    def plat_tract(
            self, tractObj, write_tract=None, ld=None,
            allow_ld_defaults=None):
        """Project a Tract object onto an existing Plat object. Optionally,
        write the tract description at the bottom with `write_tract=True`.
        If `write_tract` is unspecified, it will default to whatever the
        Plat settings say (i.e. in `platObject.settings.write_tracts`)."""

        if allow_ld_defaults is None:
            allow_ld_defaults = self.allow_ld_defaults

        twp, rge = tractObj.twp, tractObj.rge
        sec = tractObj.sec
        if sec == 'secError':
            sec = 0
        sec = str(int(sec)).rjust(2, '0')

        # If the user fed in a LDDB or TwpLD, rather than a LotDefinitions
        # object, get the appropriate LD from the LDDB or TLD.
        if isinstance(ld, LotDefDB):
            ld = ld.trs(
                twp + rge + sec, allow_ld_defaults=allow_ld_defaults)
        elif isinstance(ld, TwpLotDefinitions):
            ld = ld.get_ld(
                int(sec), allow_ld_defaults=allow_ld_defaults,
                force_ld_return=True)

        # If the user requested default LotDefs (based on a 'standard'
        # township) by passing 'default' for `ld`, create that LD obj.
        if ld == 'default':
            ld = LotDefinitions(int(sec))

        # Or if not specified when `.plat_tract()` was called, pull from
        # the Plat object's attributes, as long as they were set.
        if ld is None:
            if self.ld is not None:
                ld = self.ld
            elif self.tld is not None:
                ld = self.tld.get_ld(
                    int(sec), allow_ld_defaults=allow_ld_defaults,
                    force_ld_return=True)
            else:
                # Otherwise, fall back to an empty LD.
                ld = LotDefinitions()

        # Generate a SectionGrid from the Tract, and plat it.
        secGrid = SectionGrid.from_tract(tractObj, ld=ld)
        self.plat_section_grid(secGrid)

        # If not specified whether to write tract, default to settings
        if write_tract is None:
            write_tract = self.settings.write_tracts

        if write_tract:
            self.write_all_tracts([tractObj])

    def _wrap_text(
            self, text, first_line_indent=0, new_line_indent=8,
            custom_line_width=None) -> list:
        """
        Break down the text into a list of lines that should fit within
        the currently set `self.text_line_width`.
        :param custom_line_width: If specified, will use this as the
        line width, rather than `self.text_line_width`.
        :param first_line_indent: How many spaces to write at the start
        of the first line of text. (Defaults to 0)
        :param new_line_indent: How many spaces to write at the start
        of every subsequent line of text. (Defaults to 8)
        # TODO: configure these indents in Settings object.
        """

        import textwrap
        final_lines = []
        width = custom_line_width
        if width is None:
            width = self.text_line_width

        # In order to maintain linebreaks/returns, but also have desired
        # indents, we need to manually break our text by linebreak first,
        # and only then run textwrap on each resulting line.

        # First split our text by returns and linebreaks.
        text = text.replace('\r', '\n')
        rough_lines = text.split('\n')

        i = 0
        for rough_line in rough_lines:

            # Strip any pre-existing whitespace
            rough_line = rough_line.strip()

            # Construct the initial_indent. Keep in mind that we've
            # already broken the text into rough lines (by linebreak),
            # so the `initial_indent` that we pass to textwrap will
            # be identical to `subsequent_indent` for every line except
            # the first rough_line.

            # For the first rough_line, we use the first_line_indent
            initial_indent = ' ' * first_line_indent
            if i > 0:
                # For all others, we use new_line_indent.
                initial_indent = ' ' * new_line_indent

            subsequent_indent = ' ' * new_line_indent

            # Wrap rough_line into neater lines and add to final lines
            neater_lines = textwrap.wrap(
                rough_line, initial_indent=initial_indent,
                subsequent_indent=subsequent_indent, width=width)
            final_lines.extend(neater_lines)

            i += 1

        return final_lines

    def write_all_tracts(self, tracts=None, cursor='text_cursor'):
        """Write all the tract descriptions at the bottom of the plat,
        starting at the current coord of the specified `cursor`. If a
        string is NOT passed as `cursor=` (or a non-existent cursor is
        specified), it will begin at the default `.text_cursor`. The
        coord in `cursor` will also be updated as text gets written."""

        if tracts is None or self.text_box is None:
            return

        # Save line space later in by setting this variable:
        settings = self.settings

        def write_warning(num_unwritten_tracts, tracts_written):
            """Could not fit all tracts on the page. Write a warning to
            that effect at the bottom of the page."""

            # If we wrote at least one tract, we want to include the word
            # 'other', to avoid any confusion.
            other = ''
            if tracts_written > 0:
                other = ' other'

            plural = ''
            if num_unwritten_tracts > 1:
                plural = 's'

            warning = f'[No space to write {num_unwritten_tracts}{other} tract{plural}]'

            font = self.settings.tractfont
            color = Settings.RGBA_RED

            self.write_custom_text(
                text=warning, cursor=cursor, font=font, font_RGBA=color,
                override_legal_check=True)

        pull_ejector = False
        tracts_written = 0
        for tract in tracts:

            if pull_ejector or self.next_line_is_last_line:
                # We either failed to write the last full tract because it would
                # have gone outside our textbox, or the next line is the last
                # available within our textbox, and we have at least one more
                # tract yet to write. So write a warning now.
                num_unwritten = len(tracts) - tracts_written
                write_warning(num_unwritten, tracts_written)
                break

            # We will save the last line to write a warning, unless this
            # is the last tract to write.
            save_last_line = tracts_written != len(tracts) - 1

            font_RGBA = self.settings.tractfont_RGBA
            if len(tract.lotQQList) == 0 or tract.sec == 'secError':
                # If no lots/QQs were identified, or if this tract has a
                # 'secError' (i.e. it was a flawed parse where the section
                # number could not be successfully deduced -- in which case it
                # could not have been projected onto this plat), then we'll
                # write the tract in red
                font_RGBA = Settings.RGBA_RED
            write_tract_success = self.write_tract(
                cursor=cursor, tractObj=tract, font_RGBA=font_RGBA,
                save_last_line=save_last_line)
            pull_ejector = not write_tract_success

            tracts_written += 1

    def write_tract(
            self, tractObj: Tract, cursor='text_cursor', font_RGBA=None,
            override_legal_check=False, save_last_line=True) -> bool:
        """
        Write the description of the parsed pyTRS.Tract object in the
        `.text_box`, at the current coord of the specified `cursor`.
        First confirms that writing the text would not go past margins;
        and if so, will not write it. Updates the coord of the `cursor`
        used.

        :param tractObj: a pyTRS.Tract object, whose description should
        be written.
        :param cursor: The name of an existing cursor, at whose coords
        the text should be written. (Defaults to 'text_cursor')
        :param font_RGBA: A 4-tuple containing RGBA value to use
        (defaults to configuration in settings)
        :param override_legal_check: Ignore whether it is past the
        margins. (`False` by default)
        :param save_last_line: A bool, whether or not the last line
        (before the margins are broken) should be reserved -- i.e., if
        a tract will be written all the way to the end of the margin,
        this will dictate whether or not to stop before writing that
        last line (e.g., in case we want to write a warning message
        instead).
        :return: Returns a bool, whether or not every line of the tract
        was written.
        """

        if self.text_box is None:
            return False

        # Extract the text of the TRS+description from the Tract object.
        text = tractObj.quick_desc()

        # If font color not otherwise specified, pull from settings.
        if font_RGBA is None:
            font_RGBA = self.settings.tractfont_RGBA

        # Pull font from settings.
        font = self.settings.tractfont

        ejector_pull = False
        lines = self._wrap_text(text)
        lines_written = 0
        for line in lines:

            if self.next_line_is_last_line:
                if save_last_line:
                    return False
                elif lines_written == len(lines) - 1:
                    # This is the last line to write.
                    continue
                else:
                    line = f"{' ' * self.settings.new_line_indent}[...]"
                    font_RGBA = Settings.RGBA_RED
                    # Mandate this gets written by overriding legal check.
                    override_legal_check = True
                    # Bail out after this line.
                    ejector_pull = True

            # Check if we can fit what we're about to write within the margins.
            is_legal = self._check_legal_textwrite(line, font, cursor)

            if is_legal or override_legal_check:
                # Pull coord from the chosen cursor attribute
                coord = getattr(self, cursor)
                # Write the text, and set the width/height of the written text to xy_delta
                xy_delta = self._write_text(coord, line, font, font_RGBA)
                # Update the chosen cursor to the next line.
                self.next_line_cursor(xy_delta, cursor, commit=True)

            lines_written += 1

            if ejector_pull:
                return False

        return True

    def _write_text(
            self, coord: tuple, text: str, font, font_RGBA,
            draw_obj=None) -> tuple:
        """Write `text` at the specified `coord`. Returns a tuple of the
        width and height of the written text. Does NOT update a cursor.
        NOTE: This method does not care whether it goes past margins, so
            be sure to handle `._check_legal_textwrite()` before calling
            this method.
        If `draw_obj=` is not specified, it will default to
        `self.text_draw` (i.e. writing on the `.text_box`)."""

        if draw_obj is None:
            draw_obj = self.text_draw

        if draw_obj is None:
            raise TypeError(
                'Must provide PIL.ImageDraw object as `draw_obj=` on which'
                ' to write the text (or create a textbox on the Plat with'
                '`.new_textbox()` method, assuming Plat settings provide'
                'enough space for a textbox).')

        w, h = draw_obj.textsize(text, font=font)
        draw_obj.text(coord, text, font=font, fill=font_RGBA)
        return (w, h)

    def write_custom_text(
            self, text, cursor='text_cursor', font=None, font_RGBA=None,
            override_legal_check=False, suppress_next_line=False,
            **configure_cursor_update) -> tuple:
        """Write custom `text` on the image. May specify the location to
        write at by using EITHER `coord` (a tuple) OR by specifying
        `cursor` (a string). If `coord` is specified, that will take
        precedence over `cursor`. If neither is specified, it will
        default to the cursor 'text_cursor'.

        Returns the width and height of the written text; or returns
        None if nothing was written.

        Optionally specify `font` (an ImageFont object) and/or
        `font_RGBA` -- or they will be pulled from settings.

        `override_legal_check=True` (`False` by default) will ignore
        whether the attempted text goes past margins.

        `suppress_next_line=True` (`False` by default) will update the
        cursor but only right-ward (not down), unless it is past the
        margin, in which case, it will go to the 'next line'. (Same
        behavior as calling the `.same_line_cursor()` method.)

        Further, we can optionally pass the same parameters as in
        `.same_line_cursor()` and/or `.next_line_cursor()`, which have
        the same effect here:
            left_margin=<int> (or `None`)
            additional_x_px=<int>
            additional_indent=<int>"""

        if font is None:
            font = self.settings.tractfont

        if font_RGBA is None:
            font_RGBA = self.settings.tractfont_RGBA

        xy_delta = (0, 0)
        coord = getattr(self, cursor, getattr(self, 'text_cursor'))
        if self._check_legal_textwrite(text, font, cursor) or override_legal_check:
            # Write the text and get the width and height of the text written.
            xy_delta = self._write_text(coord, text, font, font_RGBA)
        else:
            return None

        # Unpacking the kwargs for configuring the same-line cursor update
        # (only used if `suppress_next_line==True` -- i.e. keeping our
        # cursor on the same line, if possible and if requested).
        additional_x_px = 0
        left_margin = None
        additional_indent = 0
        for k, v in configure_cursor_update.items():
            if k == 'additional_indent':
                additional_indent = v
            elif k == 'left_margin':
                left_margin = v
            elif k == 'additional_indent':
                additional_indent = v

        if suppress_next_line:
            self.same_line_cursor(
                xy_delta, cursor=cursor, additional_x_px=additional_x_px,
                left_margin=left_margin, additional_indent=additional_indent,
                commit=True)
        else:
            self.next_line_cursor(
                xy_delta, cursor=cursor, commit=True,
                additional_indent=additional_indent)

        return xy_delta

    def write_lots(self, secObj):
        """Write lot numbers in the top-left corner of the respective QQs."""

        def write_lot(lots_within_this_QQ: list, grid_location: tuple):

            # Get the pixel location of the NWNW corner of the section:
            xy_start = self.sec_coords[int(secObj.sec)]
            x_start, y_start = xy_start

            # Break out the grid location of the QQ into x, y
            x_grid, y_grid = grid_location

            # Calculate the pixel location of the NWNW corner of the QQ.
            # (Remember that qq_side is the length of each side of a QQ square.)
            x_start = x_start + self.settings.qq_side * x_grid
            y_start = y_start + self.settings.qq_side * y_grid

            # Offset x and y, as configured in settings.
            x_start += self.settings.lot_num_offset_px
            y_start += self.settings.lot_num_offset_px

            # And lastly, join the lots into a string, and write the text.
            self.draw.text(
                (x_start, y_start),
                text=', '.join(lots_within_this_QQ),
                font=self.settings.lotfont,
                fill=self.settings.lotfont_RGBA
            )

        # Each coords[y][x] contains a list of which lot(s) are at (x,y)
        # in this particular section.  For example, 'L1' through 'L4' in
        # a standard Section 1 correspond to the N2N2 QQ's, respectively
        # -- so...
        #       coords[0][0] -> ['L4']    # i.e. (0, 0), or the NWNW
        #       coords[0][1] -> ['L3']    # i.e. (1, 0), or the NENW
        #       coords[0][2] -> ['L2']    # i.e. (2, 0), or the NWNE
        #       coords[0][3] -> ['L1']    # i.e. (3, 0), or the NENE
        # ... and all other coords would be an empty list...
        #       coords[2][1] -> []    # i.e. (1,2), or the NESW
        #       coords[3][3] -> []    # i.e. (3,3), or the SESE
        #       ...etc.
        coords = secObj.lots_by_grid()

        for y in range(len(coords)):
            for x in range(len(coords[y])):
                lots = coords[y][x]
                if lots == []:
                    continue
                clean_lots = []
                for lot in lots:
                    # Delete leading 'L' from each lot, leaving only the digit,
                    # and append to clean_lots
                    clean_lots.append(lot.replace('L', ''))
                write_lot(clean_lots, (x, y))

    def fill_qq(self, section: int, grid_location: tuple, qq_fill_RGBA=None):
        """Fill in the QQ on the plat, in the specified `section`, at the
        appropriate `grid_location` coord (x, y) within that section,
        with the color specified in `qq_fill_RGBA`. If `qq_fill_RGBA` is
        not specified, it will pull from the Plat object's settings."""

        if section == 0:
            return

        if qq_fill_RGBA is None:
            # If not specified, pull from plat settings.
            qq_fill_RGBA = self.settings.qq_fill_RGBA

        # Get the pixel location of the NWNW corner of the section:
        xy_start = self.sec_coords[section]
        x_start, y_start = xy_start

        # Break out the grid location of the QQ into x, y
        x_grid, y_grid = grid_location

        # Calculate the pixel location of the NWNW corner of the QQ. (Remember
        # that qq_side is the length of each side of a QQ square.)
        x_start = x_start + self.settings.qq_side * x_grid
        y_start = y_start + self.settings.qq_side * y_grid

        # Draw the QQ
        self.overlay_draw.polygon(
            [(x_start, y_start),
             (x_start + self.settings.qq_side, y_start),
             (x_start + self.settings.qq_side, y_start + self.settings.qq_side),
             (x_start, y_start + self.settings.qq_side)],
            qq_fill_RGBA
        )

    def _draw_sec(self, top_left_corner, section=None):
        """Draw the 4x4 grid of a section with an ImageDraw object, at the
        specified coordinates. Optionally specify the section number
        with `section=<int>`. (Pulls sizes, lengths, etc. from `.settings`)"""

        x_start, y_start = top_left_corner

        settings = self.settings

        # Set this attribute to a shorter-named variable, just to save line space.
        qqs = settings.qq_side

        # We'll draw QQ lines, then Q lines, then Section boundary -- in
        # that order, so that the color of the higher-order lines overrules
        # the lower-order lines.

        # Draw the quarter-quarter lines.
        qq_lines = [
            [(x_start + qqs * 1, y_start), (x_start + qqs * 1, y_start + qqs * 4)],
            [(x_start + qqs * 3, y_start), (x_start + qqs * 3, y_start + qqs * 4)],
            [(x_start, y_start + qqs * 1), (x_start + qqs * 4, y_start + qqs * 1)],
            [(x_start, y_start + qqs * 3), (x_start + qqs * 4, y_start + qqs * 3)]
        ]

        for qq_line in qq_lines:
            self.draw.line(
                qq_line,
                fill=settings.qql_RGBA,
                width=settings.qql_stroke)

        # Draw the quarter lines (which divide the section in half).
        q_lines = [
            [(x_start + qqs * 2, y_start), (x_start + qqs * 2, y_start + qqs * 4)],
            [(x_start, y_start + qqs * 2), (x_start + qqs * 4, y_start + qqs * 2)]
        ]

        for q_line in q_lines:
            self.draw.line(
                q_line,
                fill=settings.ql_RGBA,
                width=settings.ql_stroke)

        # Draw a white box in the center of the section.
        x_center, y_center = (x_start + qqs * 2, y_start + qqs * 2)
        cbwh = settings.centerbox_wh
        centerbox = [
            (x_center - (cbwh // 2), y_center - (cbwh // 2)),
            (x_center - (cbwh // 2), y_center + (cbwh // 2) + 3),
            (x_center + (cbwh // 2), y_center + (cbwh // 2)),
            (x_center + (cbwh // 2), y_center - (cbwh // 2)),
        ]
        self.draw.polygon(centerbox, Settings.RGBA_WHITE)

        # Draw the outer bounds of the section.
        sec_sides = [
            [(x_start, y_start), (x_start + qqs * 4, y_start)],
            [(x_start + qqs * 4, y_start), (x_start + qqs * 4, y_start + qqs * 4)],
            [(x_start + qqs * 4, y_start + qqs * 4), (x_start, y_start + qqs * 4)],
            [(x_start, y_start + qqs * 4), (x_start, y_start)],
        ]

        for side in sec_sides:
            self.draw.line(
                side,
                fill=settings.sec_line_RGBA,
                width=settings.sec_line_stroke)

        # If requested, write in the section number
        if section is not None and settings.write_section_numbers:
            # TODO: DEBUG -- Section numbers are printing very slightly
            #   farther down than they should be. Figure out why.
            w, h = self.draw.textsize(str(section), font=settings.secfont)
            self.draw.text(
                (x_center - (w // 2), y_center - (h // 2)),
                str(section),
                fill=settings.secfont_RGBA,
                font=settings.secfont)


class MultiPlat:
    """An object to create, process, hold, and output one or more Plat
    objects -- e.g., when there are multiple T&R's from a PLSSDesc obj.

    At init, configure the look, size, fonts, etc. of all subordinate
    Plats by passing a Settings object to `settings=`. (Can also pass
    the name of a preset -- see Settings docs for more details.)

    For better results, optionally pass a LotDefDB object (or the
    filepath to a .csv file that can be read into a LotDefDB object) to
    `lddb=`, to specify how to handle lots -- i.e. which QQ's are
    intended by which lots. (See more info in `grid.LotDefDB` docs.)
    Use `allow_ld_defaults=True` to allow any townships for which lots
    have not been defined in the lddb, to instead use the default lot
    definitions for Sections 1 - 7, 18, 19, 30, and 31 (inits as `False`
    unless specified otherwise).

    MultiPlat objects can process these types of objects:
        pyTRS.PLSSDesc**, pyTRS.Tract**, SectionGrid, TownshipGrid
    (**pyTRS.Tract objects are imported in this module as `Tract`, and
    pyTRS.PLSSDesc objects are imported as `PLSSDesc`.)

    Generated Plat objects are stored in `.plats`. They are Plat objects
    but not flattened images. To get a list of flattened images from all
    of the plats, use the `.output()` method. And see `.output_to_pdf()`
    and `.output_to_png()` methods for saving to files.

    A MultiPlatQueue object is stored for each MultiPlat as `.mpq`,
    which can be added to with the `.queue()` method (or `.queue_text()`
    method), and processed with the `.process_queue()` method."""

    # TODO: Wherever LDDB, TLD, or LD is referenced in a kwarg, allow it
    #   to pull from self.lddb.

    # TODO: Figure out a good way to organize the plats. I'm thinking a
    #  dict, keyed by T&R. Currently, it's a list.

    def __init__(self, settings=None, lddb=None, allow_ld_defaults=False):

        # If settings was not specified, create a default Settings object.
        if settings is None:
            settings = Settings()
        elif isinstance(settings, str):
            # If passed as a string, it should be the name of a preset.
            # Create that Settings object now. (Will throw off an error
            # if not an existing preset name.)
            settings = Settings(preset=settings)
        self.settings = settings

        # A list of generated plats
        self.plats = []

        # A MultiPlatQueue object holding PlatQueue objects (which in
        # turn hold elements/tracts that will be platted).
        self.mpq = MultiPlatQueue()

        # Try converting lddb to a pathlib.Path object (e.g., if it was
        # passed as a string). If unsuccessful, it seems the user has
        # NOT tried to pass a filepath as `lddb`.
        try:
            lddb = Path(lddb)
        except TypeError:
            pass

        # LotDefDB object for defining lots in subordinate plats (if not
        # specified when platting objects).
        if isinstance(lddb, Path):
            # If a string is passed, we assume it's a filepath to a file
            # that can be read into a LDDB object (e.g., a .csv file).
            # Convert to LDDB object now. (Will throw off errors if it
            # does not lead to a '.csv' file.)
            lddb = LotDefDB(from_csv=lddb)
        if not isinstance(lddb, LotDefDB):
            # If there's no valid LDDB by now, default to an empty LDDB.
            lddb = LotDefDB()
        self.lddb = lddb

        # Whether or not to pull default TLD's when they are not set
        # in our LotDefDB. (See `Grid.LotDefDB.get_tld()` for more info)
        self.allow_ld_defaults = allow_ld_defaults

    @staticmethod
    def from_queue(mpq, settings=None, lddb=None, allow_ld_defaults=False):
        """Generate and return a MultiPlat object from a MultiPlatQueue
        object."""

        mp_obj = MultiPlat(
            settings=settings, lddb=lddb, allow_ld_defaults=allow_ld_defaults)
        mp_obj.process_queue(mpq)
        return mp_obj

    def queue(self, plattable, twprge='', tracts=None):
        """Queue up an object for platting -- i.e. pass through the
        arguments to the `.queue()` method in the Plat's MultiPlatQueue
        object."""
        self.mpq.queue(plattable=plattable, twprge=twprge, tracts=tracts)

    def queue_text(self, text, config=None):
        """Parse the text of a PLSS land description (optionally using
        `config=` parameters -- see pyTRS docs), and add the resulting
        PLSSDesc object to this MultiPlat's queue (`.mpq`) -- by passing
        through the arguments to the `.queue_text()` method in the
        Plat's MultiPlatQueue object."""
        self.mpq.queue_text(text=text, config=config)

    def process_queue(self, queue=None, allow_ld_defaults=None):
        """Process all objects in a MultiPlatQueue object. If `queue=None`,
        the MultiPlatQueue object that will be processed is this
        MultiPlat's `.mpq` attribute."""

        if allow_ld_defaults is None:
            allow_ld_defaults = self.allow_ld_defaults

        # If a different MultiPlatQueue isn't otherwise specified, use
        # the Plat's own `.mpq` from init.
        if queue is None:
            queue = self.mpq

        stngs = self.settings
        for twprge, pq in queue.items():
            tld = self.lddb.get(twprge, None)
            pl_obj = Plat.from_twprge(
                twprge, settings=stngs, tld=tld,
                allow_ld_defaults=allow_ld_defaults)
            pl_obj.process_queue(pq)
            self.plats.append(pl_obj)

    @staticmethod
    def from_plssdesc(
            PLSSDesc_obj, settings=None, lddb=None, allow_ld_defaults=False):
        """Generate a MultiPlat from a parsed PLSSDesc object.
        (lots/QQs must be parsed within the Tracts for any QQ's to be
        filled on the resulting plats.)"""

        mp_obj = MultiPlat(
            settings=settings, lddb=lddb, allow_ld_defaults=allow_ld_defaults)

        # Generate a dict of TownshipGrid objects from the PLSSDesc object.
        twp_grids = plssdesc_to_grids(
            PLSSDesc_obj, lddb=lddb, allow_ld_defaults=allow_ld_defaults)

        # Get a dict linking the the PLSSDesc object's parsed Tracts to their
        # respective T&R's (keyed by T&R '000x000y' -- same as the twp_grids dict)
        twp_to_tract = filter_tracts_by_twprge(PLSSDesc_obj.parsedTracts)

        # Generate Plat object of each township, and append it to mp_obj.plats
        for k, v in twp_grids.items():
            pl_obj = Plat.from_township_grid(v, tracts=twp_to_tract[k], settings=settings)
            mp_obj.plats.append(pl_obj)

        return mp_obj

    @staticmethod
    def from_text(
            text, config=None, settings=None, lddb=None, allow_ld_defaults=False):
        """Parse the text of a PLSS land description (optionally using
        `config=` parameters -- see pyTRS docs), and generate Plat(s)
        for the lands described. Returns a MultiPlat object."""

        descObj = PLSSDesc(text, config=config, initParseQQ=True)
        return MultiPlat.from_plssdesc(
            descObj, settings=settings, lddb=lddb,
            allow_ld_defaults=allow_ld_defaults)

    def show(self, index: int):
        """Display one of the plat Image objects, specifically the one
        in the `.plats` list at the specified `index`."""
        self.plats[index].output().show()

    @staticmethod
    def _cull_list_to_requested_pages(list_to_cull: list, pages: list) -> list:
        """Take a list, and return a list of the same objects, but
        limited to the specified `pages`. Discards any page requests
        that do not exist (i.e. below 0 or above the total page count in
        `list_to_cull`). If `pages` is None, will return the original
        list intact (i.e. all pages)."""

        if pages is None:
            # If not specified, output all.
            return list_to_cull
        elif isinstance(pages, int):
            pages = [pages]
        else:
            pages = list(pages)

        output_list = []
        for page_num in pages:
            if page_num >= len(list_to_cull) or page_num < 0:
                pass
            else:
                output_list.append(list_to_cull[page_num])
        return output_list

    def output_to_pdf(self, filepath, pages=None):
        """Save all of the Plat images to a PDF at the specified
        `filepath`. If `pages=` is specified as an int, or list / tuple
        of ints, only the specified pages will be included. Otherwise,
        will output all pages."""

        if not confirm_file_ext(filepath, '.pdf'):
            raise ValueError('filepath must end with \'.pdf\'')

        output_list = self.output(pages=pages)

        if len(output_list) == 0:
            return

        im1 = output_list.pop(0)
        im1.save(filepath, save_all=True, append_images=output_list)

    def output_to_png(self, filepath, pages=None):
        """Save all of the Plat images to .png (or multiple .png files,
        if there is more than one Plat in `.plats`) at the specified
        `filepath`. If `pages=` is specified as an int, or list / tuple
        of ints, only the specified pages will be included. Otherwise,
        will output all pages.
        IMPORTANT: If multiple plats are output, then numbers (from
        '_000') will be added to the end of each, before the file
        extension."""

        if not confirm_file_ext(filepath, '.png'):
            raise ValueError('filepath must end with \'.png\'')

        output_list = self.output(pages=pages)

        if len(output_list) == 0:
            return
        elif len(output_list) == 1:
            output_list[0].save(filepath)
        else:
            i = 0
            ext = '.png'
            fp = filepath[:-len(ext)]
            while len(output_list) > 0:
                filepath = f"{fp}_{str(i).rjust(3,'0')}{ext}"
                output_list.pop(0).save(filepath)
                i += 1

    def output(self, pages=None) -> list:
        """Return a list of flattened Image objects from all of the Plat
        objects in `.plats`. If `pages=` is specified as an int, or list
        or tuple of ints, only the specified pages will be included.
        Otherwise, will output all pages."""
        plat_ims = []
        for p in self.plats:
            plat_ims.append(p.output().convert('RGB'))

        output_list = MultiPlat._cull_list_to_requested_pages(plat_ims, pages)

        return output_list


########################################################################
# Platting text directly
########################################################################

def text_to_plats(
        text, config=None, settings=None, lddb=None,
        output_filepath=None, allow_ld_defaults=False) -> list:
    """Parse the text of a PLSS land description (optionally using
    `config=` parameters -- see pyTRS docs), and generate plat(s) for
    the lands described. Optionally output to .png or .pdf with
    `output_filepath=` (end with '.png' or '.pdf' to specify the output
    file type).  Returns a list of Image objects of the plats.

    Configure the look, size, fonts, etc. of the Plat by passing a
    Settings object to `settings=`. (Can also pass the name of a preset
    -- see Settings docs for more details.)

    Optionally pass a LotDefDB object (or path to .csv file that can be
    read into a LotDefDB object) into `lddb=` for better results. (See
    more info in `grid.LotDefDB` docs."""

    mp = MultiPlat.from_text(
        text=text, config=config, settings=settings, lddb=lddb,
        allow_ld_defaults=allow_ld_defaults)
    if output_filepath is not None:
        if confirm_file_ext(output_filepath, '.pdf'):
            mp.output_to_pdf(output_filepath)
        elif confirm_file_ext(output_filepath, '.png'):
            mp.output_to_png(output_filepath)
    return mp.output()