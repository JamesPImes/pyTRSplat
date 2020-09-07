# Copyright (c) 2020, James P. Imes. All rights reserved.

"""Generate plat images of full Townships (6x6 grid) or single Sections
and incorporate parsed pyTRS PLSSDesc and Tract objects."""

# TODO: Add kwarg for specifying LotDefinitions for Tracts, and
#  maybe TwpLotDefinitions where appropriate. (Have already implemented
#  LDDB in at least some places.)


from PIL import Image, ImageDraw, ImageFont
from pyTRS import version as pyTRS_version
from pyTRS.pyTRS import PLSSDesc, Tract
from grid import TownshipGrid, SectionGrid, plss_to_grids, filter_tracts_by_tr
from grid import LotDefinitions, TwpLotDefinitions, LotDefDB, confirm_file
from platsettings import Settings

__version__ = '0.0.1'
__versionDate__ = '8/31/2020'
__author__ = 'James P. Imes'
__email__ = 'jamesimes@gmail.com'


class Plat:
    """An object containing an Image of a 36-section (in `.image`), as
    well as various attributes for platting on top of it. Notably,
    `.sec_coords` is a dict of the pixel coordinates for the NWNW corner
    of each of the 36 sections (keyed by integers 1 - 36, inclusive).
    NOTE: May plat a single section, with `only_section=<int>` at init."""

    def __init__(self, twp='', rge='', only_section=None, settings=None):
        self.twp = twp
        self.rge = rge
        self.TR = twp+rge

        # NOTE: settings can be specified as a Settings object, as a
        # filepath (str) to a settings data .txt (which are created via
        # the `.save_to_file()` on a Settings object), or by passing the
        # name of an already saved preset (also as a string).
        if isinstance(settings, str):
            if settings.lower().endswith('.txt'):
                try:
                    settings = Settings.from_file(settings)
                except:
                    settings = None
            else:
                try:
                    settings = Settings.preset(settings)
                except:
                    settings = None

        # If settings was not specified, create a default Settings object.
        if settings is None:
            settings = Settings()
        self.settings = settings
        dim = settings.dim

        self.image = Image.new('RGBA', dim, Settings.RGBA_WHITE)
        self.draw = ImageDraw.Draw(self.image, 'RGBA')

        # A dict of the sections and the (x,y) coords of their NWNW corner:
        self.sec_coords = {}

        # Draw the standard 36 sections, or the `only_section` (an int).
        # (If `only_section` is None, then will draw all 36 in 6x6 grid.
        # If specified, will draw only that section.)
        self._draw_all_sections(only_section=only_section)
        self.header = self._gen_header(only_section=only_section)

        if self.settings.write_header:
            self._write_header()

        # Keeping track of the current position where text (e.g., tracts
        # etc.) can be written -- i.e. where we've written up to, and
        # where we can still write at in x,y pixel coordinates
        self.text_cursor = self._reset_cursor()
        # NOTE: Other cursors can also be created
        #   ex: This would create a new cursor at the original x,y
        #       coords and accessed as `platObj.highlighter`:
        #           >>> platObj._reset_cursor(cursor='highlighter')
        #   ex: This would create a new cursor at the specified x,y
        #       coords (120,180) and accessed as `platObj.highlighter`:
        #           >>> platObj.set_cursor(120, 180, cursor='highlighter')

        # Overlay on which we'll plat QQ's
        self.overlay = Image.new('RGBA', self.image.size, (255, 255, 255, 0))
        self.overlay_draw = ImageDraw.Draw(self.overlay, 'RGBA')

        # TODO: self.cursor = <the current position where tract text, etc. can be written>
        #   i.e. Keep track where we've written up to, and where we can still write at in
        #   x,y pixel coordinates.


    def _gen_header(self, only_section=None):
        """Generate the text of a header containing the T&R and/or
        Section number."""

        twptxt = ''
        if '' not in [self.twp, self.rge]:
            # If twp and rge were specified
            twptxt = '{Township/Range Error}'

            twp = str(self.twp)
            rge = str(self.rge)

            twpNum = '0'
            rgeNum = '0'
            NS = 'undefined'
            EW = 'undefined'
            twprge_fail = False

            if twp[-1].lower() == 'n':
                NS = 'North'
                twpNum = twp[:-1]
            elif twp[-1].lower() == 's':
                NS = 'South'
                twpNum = twp[:-1]
            else:
                twprge_fail = True

            if rge[-1].lower() == 'e':
                EW = 'East'
                rgeNum = rge[:-1]
            elif rge[-1].lower() == 'w':
                EW = 'West'
                rgeNum = rge[:-1]
            else:
                twprge_fail = True

            if 'TRerr' in [twp, rge]:
                twptxt = '{Township/Range Error}'
            elif twprge_fail:
                twptxt = ''
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
        w, h = self.settings.dim

        # We'll horizontally center our plat on the page.
        x_start = (w - (self.settings.qq_side * 4 * 6)) // 2

        # The plat will start this many px below the top of the page.
        y_start = self.settings.y_top_marg

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

        # Generate section(s) on the plat, and number them.
        if only_section is not None:
            # If drawing only one section
            self._draw_sec((x_start, y_start), section=only_section)
            self.sec_coords[int(only_section)] = (x_start, y_start)
        else:
            # If drawing all 36 sections
            for i in range(6):
                for j in range(6):
                    sec_num = sec_nums.pop(0)
                    cur_x = x_start + self.settings.qq_side * 4 * j
                    cur_y = y_start + self.settings.qq_side * 4 * i
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

    def _reset_cursor(self, cursor='text_cursor', commit=True) -> tuple:
        """Return the original coord (x,y) of where bottom text may be
        written, per settings. If `commit=True` (on by default), the
        coord will be stored to the Setting object.
        If a string is NOT passed as `cursor`, the committed coord will
        be set to `.text_cursor`. However, if the particular cursor IS
        specified, it will save the resulting coord to that attribute
        name (so long as `commit=True`).
          ex: 'setObj._reset_cursor(cursor='highlight', commit=True)
                -> setObj.highlight == (x, y)
                # where x,y are the starting coord."""

        stngs = self.settings
        x = stngs.bottom_text_indent
        y = stngs.y_top_marg + stngs.qq_side * 4 * 6 + stngs.y_px_before_tracts
        coord = (x, y)

        # Only if `commit=True` do we set this.
        if commit:
            setattr(self, cursor, coord)

        # And return the coord.
        return coord

    def set_cursor(self, x, y, cursor='text_cursor'):
        """Set the cursor to the specified x and y coords.  If a string
        is NOT passed as `cursor`, the committed coord will be set to
        `.text_cursor`. However, if the particular cursor IS specified,
        it will save the resulting coord to that attribute name."""
        setattr(self, cursor, (x, y))

    def update_cursor(
            self, x_delta, y_delta, cursor='text_cursor', commit=True) -> tuple:
        """Return an updated coord (x,y) of where bottom text may be
        written, per settings. If `commit=True` (on by default), the
        coord will be stored to the Setting object.
        If a string is NOT passed as `cursor`, the committed coord will
        be set to `.text_cursor`. However, if the particular cursor IS
        specified, it will save the resulting coord to that attribute
        name (so long as `commit=True`).
          ex: 'setObj.update_cursor(cursor='highlight', commit=True)
                -> setObj.highlight == (x, y)
                # where x,y are the updated coord.
        IMPORTANT: If `cursor` is specified but does not already exist,
        it will be based off `.text_cursor`."""

        # Pull the specified cursor. If it does not already exist as an
        # attribute in this object, it will fall back to `.text_cursor`,
        # which exists for every Settings object, per init.
        x0, y0 = getattr(self, cursor, getattr(self, 'text_cursor'))
        coord = (x0 + x_delta, y0 + y_delta)

        # Only if `commit=True` do we set this.
        if commit:
            setattr(self, cursor, coord)

        return coord

    def output(self, filepath=None):
        """Merge the drawn overlay (i.e. filled QQ's) onto the base
        township plat image and return an Image object. Optionally save
        to file if `filepath=<filepath>` is specified."""
        merged = Image.alpha_composite(self.image, self.overlay)

        # TODO: Add the option with *args to specify which layers get
        #   included in the output. That also will require me to have
        #   separate layers for QQ's, the grid, labels, etc.
        #   And that, in turn, will require me to change methods to
        #   /plat/ onto multiple layers.

        if filepath is not None:
            merged.save(filepath)

        return merged

    def plat_section(self, SecObj, qq_fill_RGBA=None):
        """Take the SectionGrid object and fill any ticked QQ's (per the
        `SectionGrid.QQgrid` values)."""
        secNum = int(SecObj.sec)
        # TODO: Handle secError
        for coord in SecObj.filled_coords():
            self.fill_qq(secNum, coord, qq_fill_RGBA=qq_fill_RGBA)
        if self.settings.write_lot_numbers:
            self.write_lots(SecObj)

    @staticmethod
    def from_section_grid(section : SectionGrid, tracts=None, settings=None):
        """Return a section-only plat generated from a SectionGrid object."""
        # TODO: Write this method for a section-only plat, rather than 6x6 grid.
        platObj = Plat(
            twp=section.twp,
            rge=section.rge,
            settings=settings,
            only_section=section.sec)
        platObj.plat_section(section)
        platObj.write_all_tracts(tracts)
        return platObj

    @staticmethod
    def from_township_grid(township, tracts=None, settings=None):
        """Return a Plat object generated from a TownshipGrid object."""
        twp = township.twp
        rge = township.rge
        platObj = Plat(twp=twp, rge=rge, settings=settings)
        platObj.plat_township(township=township, tracts=tracts)
        return platObj

    def plat_township(self, township, tracts=None):
        """Project a TownshipGrid object onto an existing Plat object."""

        # Generate the list of sections that have anything in them.
        sec_list = township.filled_sections()

        # Plat each Section's filled QQ's onto our new overlay.
        for sec in sec_list:
            if self.settings.write_lot_numbers:
                # If so configured in settings, write lot numbers onto QQ's
                self.write_lots(sec)
            self.plat_section(sec)

        # Write the Tract data to the bottom of the plat.
        self.write_all_tracts(tracts)

        return self.output()

    def write_all_tracts(self, tracts=None):
        """Write all the tract descriptions at the bottom of the plat."""
        if tracts is None or not self.settings.write_tracts:
            return

        # Save line space later in by setting this variable:
        settings = self.settings

        y_spacer = 10  # This many px between tracts.
        total_px_written = 0

        # starting coord for the first tract.
        start_x, start_y = self.text_cursor
        x, y = (start_x, start_y)

        max_px = self.image.height - start_y - settings.y_bottom_marg

        tracts_written = 0
        for tract in tracts:
            # x and y are returned from write_tract(); x stays the same, but y is updated
            last_y = y
            font_RGBA = self.settings.tractfont_RGBA
            if len(tract.lotQQList) == 0:
                # If no lots/QQs were identified, we'll write the tract in red
                font_RGBA = Settings.RGBA_RED
            x, y = self._write_tract((x, y), tract, font_RGBA=font_RGBA)
            y += y_spacer
            total_px_written = y - start_y
            tracts_written += 1
            if total_px_written >= max_px:
                if tracts_written + 1 >= len(tracts):
                    # No more or only 1 more tract to write.
                    continue
                else:
                    # Write a warning that we ran out of space to write tracts.
                    warning = '[AND OTHER TRACTS]'
                    self.draw.text(
                        (x, y),
                        warning,
                        font=self.settings.tractfont,
                        fill=Settings.RGBA_RED)
                    break

    def _write_tract(self, start_xy, TractObj, font_RGBA=None):
        """Write the parsed Tract object on the page."""

        if font_RGBA is None:
            font_RGBA = self.settings.tractfont_RGBA

        x, y = start_xy
        tract_text = TractObj.quick_desc()
        w, h = self.draw.textsize(tract_text, font=self.settings.tractfont)
        self.draw.text(
            start_xy,
            tract_text,
            font=self.settings.tractfont,
            fill=font_RGBA)
        return x, y + h

    #TODO: def write_custom_text(self, start_xy, text, font_RGBA)

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
        """Fill in the QQ at the `grid_location` coords, of the specified
        `section`, on the `plat`, with the color specified in qq_fill_RGBA."""

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

    def _draw_sec(self, xy_start, section=None):
        """Draw the 4x4 grid of a section with a ImageDraw object, at the
        specified coordinates. Optionally specify the section number with
        `section=<int>`. If `settings=<Settings object> is not specified,
        default settings will be used."""

        x_start, y_start = xy_start

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
    objects -- e.g., when there are multiple T&R's from a PLSSDesc obj."""

    def __init__(self, settings=None):
        if settings is None:
            settings = Settings()
        self.settings = settings

        # A list of generated plats
        self.plats = []

    @staticmethod
    def from_multiple(*plat_targets, settings=None):
        """Generate a cohesive MultiPlat from multiple sources,
        optionally of different types."""
        # TODO: Finish writing this method.
        mp_obj = MultiPlat(settings=settings)

        # A list of generated plats
        mp_obj.plats = []

        PLSSDesc_objs = []
        Tract_objs = []
        for p in plat_targets:
            if isinstance(p, TownshipGrid):
                mp_obj.plats.append(Plat.from_township_grid(p, settings=mp_obj.settings))
            elif isinstance(p, SectionGrid):
                mp_obj.plats.append(Plat.from_section_grid(p, settings=mp_obj.settings))
            elif isinstance(p, PLSSDesc):
                PLSSDesc_objs.append(p)
            elif isinstance(p, Tract):
                Tract_objs.append(p)
        for d in PLSSDesc_objs:
            Tract_objs.extend(d.parsedTracts)
        twp_dict = {}
        for t in Tract_objs:
            twp_dict = filter_tracts_by_tr(t, twp_dict)
        for township_key, v in twp_dict.items():
            # TODO: plat_plss on each t,v
            pass

    @staticmethod
    def from_PLSSDesc(PLSSDesc_obj, settings=None, lddb=None):
        """Generate a MultiPlat from a parsed PLSSDesc object.
        (lots/QQs must be parsed within the Tracts for this to work.)"""

        mp_obj = MultiPlat(settings=settings)

        # Generate a dict of TownshipGrid objects from the PLSSDesc object.
        twp_grids = plss_to_grids(PLSSDesc_obj, lddb=lddb)

        # Get a dict linking the the PLSSDesc object's parsed Tracts to their respective
        # T&R's (keyed by T&R '000x000y' -- same as the twp_grids dict)
        twp_to_tract = filter_tracts_by_tr(PLSSDesc_obj.parsedTracts)

        # Generate Plat object of each township, and append it to mp_obj.plats
        for k, v in twp_grids.items():
            pl_obj = Plat.from_township_grid(v, tracts=twp_to_tract[k], settings=settings)
            mp_obj.plats.append(pl_obj)

        return mp_obj

    @staticmethod
    def from_text(text, config=None, settings=None, lddb=None):
        """Parse the text of a PLSS land description, and generate plat(s)
        for the lands described. Returns a MultiPlat object of the plats."""

        # If the user passed a filepath to a .csv file as `lddb`, create a
        # LotDefDB object from that file now, and then pass that forward.
        if confirm_file(lddb, '.csv'):
            lddb = LotDefDB.from_csv(lddb)

        descObj = PLSSDesc(text, config=config, initParseQQ=True)
        return MultiPlat.from_PLSSDesc(descObj, settings=settings, lddb=lddb)

    def show(self, index: int):
        """Display one of the plat Images, specifically the one in the
        `.plats` list at the specified `index`."""
        try:
            self.plats[index].output().show()
        except:
            return None

    def output_to_pdf(self, filepath):
        """Save all of the Plat images to a PDF at the specified
        `filepath`."""
        if not filepath.lower().endswith('.pdf'):
            raise Exception('Error: filepath should end with `.pdf`')
            return
        plat_ims = self.output()
        if len(plat_ims) == 0:
            return
        im1 = plat_ims.pop(0)
        im1.save(filepath, save_all=True, append_images=plat_ims)

    def output_to_png(self, filepath):
        """Save all of the Plat images to PNG(s) at the specified
        `filepath`. IMPORTANT: If there are multiple plats, then each
        numbers (from '_000') will be added to the end of each, before
        the file extension."""
        if not filepath.lower().endswith('.png'):
            raise Exception('Error: filepath should end with `.png`')
            return
        plat_ims = self.output()

        if len(plat_ims) == 0:
            return
        elif len(plat_ims) == 1:
            plat_ims[0].save(filepath)
        else:
            i = 0
            ext = '.png'
            fp = filepath[:-len(ext)]
            while len(plat_ims) > 0:
                filepath = f"{fp}_{str(i).rjust(3,'0')}{ext}"
                plat_ims.pop(0).save(filepath)
                i += 1

    def output(self) -> list:
        """Return a list of the Plat images."""
        plat_ims = []
        for p in self.plats:
            plat_ims.append(p.output().convert('RGB'))
        return plat_ims


class PlatQueue(list):
    """A list object to hold the objects that will be projected onto a
    Plat object, or into a MultiPlat object."""
    def __init__(self, *queue_items):
        super().__init__()
        for item in queue_items:
            if not isinstance(item, tuple):
                raise TypeError(
                    'items in a PlatQueue must be tuple, each containing a '
                    'plattable object, and optionally Tract objects (or None)')
            self.queue(item)

    def queue(self, plattable, tracts=None):
        self.append((plattable, tracts))


# TODO: Implement PlatQueue objects into Plat and MultiPlat objects:
#   Add items to be projected onto the plat (together with their Tract
#   objects). Then add a method for each Plat to project them all at the
#   same time.


########################################################################
# Platting text directly
########################################################################

def text_to_plats(text, config=None, settings=None, lddb=None, output_filepath=None) -> list:
    """Parse the text of a PLSS land description, and generate plat(s)
    for the lands described. Optionally output to .png or .pdf with
    `output_filepath=` (end with '.png' or '.pdf' to specify the output
    file type).  Returns a list of Image objects of the plats."""

    mp = MultiPlat.from_text(text=text, config=config, settings=settings, lddb=lddb)
    if output_filepath is not None:
        if output_filepath.lower().endswith('.pdf'):
            mp.output_to_pdf(output_filepath)
        elif output_filepath.lower().endswith('.png'):
            mp.output_to_png(output_filepath)
    return mp.output()


########################################################################
# Sample / testing:
#
# lddb_fp = LotDefDB.from_csv(r'C:\Users\James Imes\Box\Programming\pyTRS_plotter\assets\examples\SAMPLE_LDDB.csv')
# set1 = Settings()
# set1.write_lot_numbers = True
# descrip = 'T154N-R97W Sec 01: Lots 1 - 3, S2NE, Sec 25: Lots 1 - 8'
# # As a list:
# ttp = text_to_plats(descrip, config='cleanQQ', lddb=lddb_fp, settings=set1)
# ttp[0].show()
# # Or as a MultiPlat object:
# mp = MultiPlat.from_text(descrip, config='cleanQQ', lddb=lddb_fp, settings='letter')
# mp.show(0)

