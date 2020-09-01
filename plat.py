# Copyright (C) 2020, James P. Imes, all rights reserved.

"""A basic interpreter for parsed PLSSDesc and Tract objects, for
converting them to a grid, and basic platting."""

from pyTRS import pyTRS
from pyTRS import version as pyTRS_version
from PIL import Image, ImageDraw, ImageFont

__version__ = '0.0.1'
__versionDate__ = '8/31/2020'
__author__ = 'James P. Imes'
__email__ = 'jamesimes@gmail.com'

# TODO: Handle sections that didn't generate any lots/QQ's (e.g., m&b etc.).

# TODO: Generate a function for importing an entire section's worth of lot definitions
#  (from csv maybe?)


class Township():
    """A single Township/Range, and its 36 sections."""

    # Sections 1-6, 13-18, and 25-30 (inclusive) are east-to-west (i.e. right-to-left)
    # -- all other sections are left-to-right.
    right_to_left_sections = list(range(1,7)) + list(range(13,19)) + list(range(25,31))

    def __init__(self, twp='', rge='', nonstandard_lot_definitions=None):

        # If used, `nonstandard_lot_definitions` must be a dict, keyed
        # by EACH section (as an integer) that contains nonstandard
        # lots-to-QQ definitions, thus:
        #
        # nonstandard_lot_definitions = {
        #        1: {'L1': 'SENW', 'L2': 'SWNW', 'L3': 'NESW'},
        #        25: {'L1': 'N2NE', 'L2': 'N2NW'}
        #    }

        total_sections = 36

        self.twp = twp
        self.rge = rge
        self.TR = twp + rge
        self.sections = {}

        # Sections "snake" from the NE corner of the township west then
        # down, then they cut back east, then down and west again, etc.,
        # thus:
        #           6   5   4   3   2   1
        #           7   8   9   10  11  12
        #           18  17  16  15  14  13
        #           19  20  21  22  23  24
        #           30  29  28  27  26  25
        #           31  32  33  34  35  36
        #
        # ...so accounting for this is a little trickier:
        for secNum in range(1, total_sections + 1):
            x = (secNum - 1) // 6
            if secNum in Township.right_to_left_sections:
                y = -secNum % 6
            else:
                y = secNum % 6
            self.sections[secNum] = {
                'coord': (x, y),
                'section_data': Section.from_TwpRgeSec(
                    twp=twp, rge=rge, sec=secNum, defaultNS='n', defaultEW='w')
            }

        if isinstance(nonstandard_lot_definitions, dict):
            for key, val in nonstandard_lot_definitions.items():
                try:
                    self.apply_lot_definitions(key, val)
                except:
                    raise Exception('Error: lot_definitions improperly formatted. '
                                    'See documentation for proper formatting.')

    def apply_lot_definitions(self, section_number : int, lot_definitions : dict):
        if isinstance(lot_definitions, dict):
            raise TypeError('lot_definitions must be dict')
        self.sections[int(section_number)]['section_data'].lot_definitions = lot_definitions

    def filled_sections(self):
        x_sec = []
        for secNum, val in self.sections.items():
            if val['section_data'].has_any():
                x_sec.append(val['section_data'])
        return x_sec


class Section():

    # A few default lot_definitions, based on standard 36-section
    # Township grid. (Sections along the north and west boundaries of
    # the township have 'expected' lot locations. In practice, these
    # will rarely be the only lots in a township, and they are not
    # always consistent, even within these sections. Even so, it is
    # better than nothing.)
    def_LD_01_thru_05 = {
        'L1': 'NENE',
        'L2': 'NWNE',
        'L3': 'NENW',
        'L4': 'NWNW'
    }

    def_LD_06 = {
        'L1': 'NENE',
        'L2': 'NWNE',
        'L3': 'NENW',
        'L4': 'NWNW',
        'L5': 'SWNW',
        'L6': 'NWSW',
        'L7': 'SWSW',
    }

    def_LD_07_18_30_31 = {
        'L1': 'NWNW',
        'L2': 'SWNW',
        'L3': 'NWSW',
        'L4': 'SWSW'
    }

    # A backstop lot_definitions.
    def_LD_na = {}

    def __init__(self, trs='', lot_definitions=None):
        self.trs = trs.lower()
        twp, rge, sec = pyTRS.break_trs(trs)
        self.twp = twp
        self.rge = rge
        self.sec = sec
        self.tr = twp+rge

        try:
            secNum = int(sec)
        except:
            secNum = 0

        if lot_definitions is None:
            if secNum > 0 and secNum <= 5:
                lot_definitions = Section.def_LD_01_thru_05
            elif secNum == 6:
                lot_definitions = Section.def_LD_06
            elif secNum in [7, 18, 30, 31]:
                lot_definitions = Section.def_LD_07_18_30_31
            else:
                lot_definitions = Section.def_LD_na

        self.lot_definitions = lot_definitions

        # A dict for the 16 aliquot divisions of a standard section,
        # with (0, 0) being NWNW and (3, 3) being SESE -- i.e. beginning
        # at the NWNW, and running east and south. The nested dict for
        # each QQ contains the x,y coordinates in the grid, and whether
        # that QQ has been included -- i.e. 'val', which is either
        # 0 ('nothing') or 1 ('something') to track whether the QQ
        # (or equivalent Lot) was identified in the tract description.
        self.QQgrid = {
            'NWNW': {'coord':(0, 0), 'val': 0},
            'NENW': {'coord':(1, 0), 'val': 0},
            'NWNE': {'coord':(2, 0), 'val': 0},
            'NENE': {'coord':(3, 0), 'val': 0},
            'SWNW': {'coord':(0, 1), 'val': 0},
            'SENW': {'coord':(1, 1), 'val': 0},
            'SWNE': {'coord':(2, 1), 'val': 0},
            'SENE': {'coord':(3, 1), 'val': 0},
            'NWSW': {'coord':(0, 2), 'val': 0},
            'NESW': {'coord':(1, 2), 'val': 0},
            'NWSE': {'coord':(2, 2), 'val': 0},
            'NESE': {'coord':(3, 2), 'val': 0},
            'SWSW': {'coord':(0, 3), 'val': 0},
            'SESW': {'coord':(1, 3), 'val': 0},
            'SWSE': {'coord':(2, 3), 'val': 0},
            'SESE': {'coord':(3, 3), 'val': 0}
        }

    @staticmethod
    def from_TwpRgeSec(twp='', rge='', sec='', defaultNS='n', defaultEW='w',
                      lot_definitions=None):
        """Construct a Section with Twp, Rge, and Section separately."""
        if isinstance(twp, int):
            twp = str(twp) + defaultNS
        if isinstance(rge, int):
            rge = str(rge) + defaultEW
        if isinstance(sec, int):
            sec = str(sec).rjust(2, '0')

        trs = twp + rge + sec

        return Section(trs, lot_definitions=lot_definitions)

    @staticmethod
    def from_tract(TractObj : pyTRS.Tract, lot_definitions=None):
        """Create a Section object from a pyTRS.Tract object and
        incorporate the lotList and QQList."""
        twp, rge, sec = TractObj.twp, TractObj.rge, TractObj.sec
        secObj = Section.from_TwpRgeSec(twp, rge, sec, lot_definitions=lot_definitions)
        secObj.incorporate_tract(TractObj)

        return secObj

    def incorporate_tract(self, TractObj : pyTRS.Tract):
        self.incorporate_QQList(TractObj.QQList)
        self.incorporate_lotList(TractObj.lotList)

    def incorporate_lotList(self, lotList : list):

        # QQ equivalents to Lots
        equiv_qq = []

        # Convert each lot to its equivalent QQ, per the lot_definitions
        for lot in lotList:
            # Cull lot divisions (i.e. 'N2 of L1' to just 'L1')
            lot = lot.split(' ')[-1]
            try:
                equiv_qq.append(self.lot_definitions[lot])
            except:
                raise Exception(f'Error: Unhandled lot: {lot}. '
                                f'Define `lot_definitions` for section {self.sec}')
        final_equiv_qq = []

        # Check if the lot comprises multiple QQ's (e.g., 'L1' --> 'NENE' and 'NWNE')
        for qq in equiv_qq:
            qq_unpacked = [qq]
            if '2' in qq or '½' in qq or qq.lower() == 'all':
                qq_unpacked = pyTRS.unpack_aliquots(qq)
            final_equiv_qq.extend(qq_unpacked)

        self.incorporate_QQList(final_equiv_qq)

    def incorporate_QQList(self, QQList : list):
        for qq in QQList:
            self.QQgrid[qq]['val'] = 1

    def output_plat(self, includeHeader=False) -> str:
        """Output a plat (as a string) of the Section grid values."""

        ar = self.output_array()
        for row in ar:  # TESTING
            print(row)  # TESTING
        total_columns = len(ar[0])
        total_rows = len(ar)
        box_width = 4
        box_height = 1
        total_width = 1 + total_columns * (box_width + 1)

        header = '=' * total_width + '\n' + self.trs.center(total_width)

        plat_txt = '=' * total_width
        rows_written = 0
        for row in ar:
            drawn_row = '|'
            for col in row:
                draw = ' ' * box_width
                if col != 0:
                    draw = 'X' * box_width

                drawn_row = drawn_row + draw + '|'
            plat_txt = plat_txt + ( '\n' + drawn_row ) * box_height
            rows_written += 1
            if rows_written != total_rows:
                plat_txt = plat_txt + '\n' + '|'
                plat_txt = plat_txt + ('-' * box_width + '+') * (total_columns - 1)
                plat_txt = plat_txt + '-' * box_width + '|'

        plat_txt = plat_txt + '\n' + '=' * total_width

        return (header + '\n') * includeHeader + plat_txt

    def output_array(self) -> list:
        """Convert the grid to an array (oriented NWNW to SESE)"""

        max_x = 0
        max_y = 0
        for qq in self.QQgrid.values():
            if qq['coord'][0] > max_x:
                max_x = qq['coord'][0]
            if qq['coord'][1] > max_y:
                max_y = qq['coord'][1]

        # Create an array of all zero-values, with equal dimensions as
        # in the Section.QQgrid (which is 4x4 in a standard section).
        ar = [[0 for _a in range(max_x + 1)] for _b in range(max_y + 1)]

        for qq in self.QQgrid.values():
            x = qq['coord'][0]
            y = qq['coord'][1]
            if qq['val'] != 0:
                ar[y][x] = qq['val']

        return ar

    def filled_coords(self) -> list:
        """Return a list of coordinates in the Section that are filled."""
        ar = self.output_array()
        filled = []
        for y in range(len(ar)):
            for x in range(len(ar[y])):
                if ar[y][x] != 0:
                    filled.append((x,y))
        return filled

    def has_any(self):
        """Return a bool, whether at least one QQ is filled."""
        ar = self.output_array()
        for i in ar:
            for j in i:
                if j != 0:
                    return True
        return False


def plss_to_grid(PLSSDescObj: pyTRS.PLSSDesc) -> dict:
    """Generate a dict of all townships (keyed by T&R) in a parsed
    PLSSDesc object."""
    tl = PLSSDescObj.parsedTracts

    all_twps = {}
    # tract_sorter = {}
    for tractObj in tl:
        twp, rge, sec = pyTRS.break_trs(tractObj.trs)
        if twp == 'TRerr' or sec == 'secError':
            # TODO: handle error parses.
            print('ruh-roh')
            continue
        elif twp+rge not in all_twps:
            all_twps[twp + rge] = Township(twp=twp, rge=rge)
            # tract_sorter[twp+rge] = [tractObj]
        else:
            pass
            # tract_sorter[twp+rge].append(tractObj)
        all_twps[twp + rge].sections[int(sec)]['section_data'].incorporate_tract(tractObj)

    return all_twps


########################################################################
# Platting with PIL
########################################################################

def plat_twp(township: Township, output_file=None, RGB=(255, 0, 0), tracts=None) -> Image:
    """Generate a plat of a Township, and optionally save to
    output_file. Returns an Image object."""

    twpfnt = ImageFont.truetype(r'C:\WINDOWS\FONTS\ARIAL.TTF', 48)
    tractfnt = ImageFont.truetype(r'C:\WINDOWS\FONTS\ARIAL.TTF', 28)

    # RGBA value for the fill of the QQ squares.
    r, g, b = RGB
    RGBA = (r, g, b, 100)

    ####################################################################
    # im_dict is the pixel of the NWNW corner of the respective section,
    # on the tplat base img. Each QQ square is 47x47 pixels (or nearly).
    # But some minor tweaks are needed (until I get around to cleaning
    # up the base image).

    im_dict = {
        1: (1217, 163)
    }

    for i in range(2, 7):
        x, y = im_dict[i - 1]
        im_dict[i] = (x - 47 * 4, y)

    x, y = im_dict[6]
    im_dict[7] = (x, y + 47 * 4 + 1)

    for i in range(8, 13):
        x, y = im_dict[i - 1]
        im_dict[i] = (x + 47 * 4, y)

    x, y = im_dict[12]
    im_dict[13] = (x, y + 47 * 4 + 1)

    for i in range(14, 19):
        x, y = im_dict[i - 1]
        im_dict[i] = (x - 47 * 4, y)

    x, y = im_dict[18]
    im_dict[19] = (x, y + 47 * 4 + 1)

    for i in range(20, 25):
        x, y = im_dict[i - 1]
        im_dict[i] = (x + 47 * 4, y)

    x, y = im_dict[24]
    im_dict[25] = (x, y + 47 * 4 + 1)

    for i in range(26, 31):
        x, y = im_dict[i - 1]
        im_dict[i] = (x - 47 * 4, y)

    x, y = im_dict[30]
    im_dict[31] = (x, y + 47 * 4 + 1)

    for i in range(32, 37):
        x, y = im_dict[i - 1]
        im_dict[i] = (x + 47 * 4, y)

    ####################################################################

    def gen_overlay(image):
        overlay = Image.new('RGBA', image.size, (255, 255, 255, 0))
        drawObj = ImageDraw.Draw(overlay, 'RGBA')

        return overlay, drawObj

    def draw_qq(drawObj, section: int, grid_location: tuple, RGBA):
        """Draw the QQ """

        s_len = 46  # length of square side (in px)

        # Get the pixel location of the NWNW corner of the section:
        xy_start = im_dict[section]
        x_start, y_start = xy_start

        x_grid, y_grid = grid_location

        # Get the pixel location of the NWNW corner of the QQ, per the grid_location
        x_start = x_start + s_len * x_grid
        y_start = y_start + s_len * y_grid

        # Weird offset in the base image requires some semi-manual tweaking...
        if y_grid >= 2:
            y_start += 1
            if section >= 13:
                y_start += 1
            if section >= 31:
                y_start += 1

        # Draw the QQ
        drawObj.polygon(
            [(x_start, y_start), (x_start + s_len, y_start),
             (x_start + s_len, y_start + s_len), x_start, y_start + s_len],
            RGBA
        )

    def plat_section(drawObj, SecObj):
        """Take the Section object and draw any filled QQ's (per the
        Section.grid)."""
        secNum = int(SecObj.sec)
        # TODO: Handle secError
        for coord in SecObj.filled_coords():
            draw_qq(drawObj, secNum, coord, RGBA)

    def write_twprge(im):
        """Write the T&R at the top of the page."""

        if twp != 'TRerr':
            twpNum, NS, rgeNum, EW = pyTRS.decompile_tr(twp + rge)
            if NS == 'n':
                NS = 'North'
            else:
                NS = 'South'
            if EW == 'w':
                EW = 'West'
            else:
                EW = 'East'
            twptxt = f'Township {twpNum} {NS}, Range {rgeNum} {EW}'
        else:
            twptxt = '{Township/Range Error}'
        text_draw = ImageDraw.Draw(im)
        W, H = new_plat.size
        w, h = text_draw.textsize(twptxt, font=twpfnt)
        text_draw.text(((W - w) / 2, 48), twptxt, font=twpfnt, fill=(0, 0, 0, 100))

    def write_all_tracts(im):
        if tracts is None:
            return
        y_spacer = 10  # This many px between tracts.
        total_px_written = 0

        text_draw = ImageDraw.Draw(im)

        # starting coord for the first tract.
        start_x = 100
        start_y = 1350
        x, y = (start_x, start_y)

        min_y_margin = 80
        max_px = im.height - start_y - min_y_margin

        tracts_written = 0
        for tract in tracts:
            # x and y are returned from write_tract(); x stays the same, but y is updated
            last_y = y
            RGBA = (0, 0, 0, 100)
            if len(tract.lotQQList) == 0:
                # If no lots/QQs were identified, we'll write the tract in red
                RGBA = (255, 0, 0, 100)
            x, y = write_tract(text_draw, (x, y), tract, RGBA=RGBA)
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
                    text_draw.text((x, y), warning, font=tractfnt, fill=(255, 0, 0, 100))
                    break

    def write_tract(drawObj, start_xy, TractObj, RGBA = (0, 0, 0, 100)):
        """Write the parsed Tract object on the page."""
        x, y = start_xy
        tract_text = TractObj.quick_desc()
        w, h = drawObj.textsize(tract_text, font=tractfnt)
        drawObj.text(start_xy, tract_text, font=tractfnt, fill=RGBA)
        return x, y + h

    def merge_plat(base, overlay):
        """Merge the drawn overlay (i.e. filled QQ's) onto the base
        township plat image, draw Township and Tract info, and return
        as an Image object."""
        return Image.alpha_composite(base, overlay)

    # Get our new plat Image object, the overlay, and a Draw object for the overlay
    new_plat = Image.open(r'assets/tplat.png').convert('RGBA')
    overlay, drawObj = gen_overlay(new_plat)

    # Generate the list of sections that have anything in them.
    sec_list = township.filled_sections()
    twp = township.twp
    rge = township.rge

    # Plat each Section's filled QQ's onto our new overlay.
    for sec in sec_list:
        plat_section(drawObj, sec)

    # Merge the overlay onto the plat.
    merged = merge_plat(new_plat, overlay)

    # Write the Township / Range as a header.
    write_twprge(merged)

    # Write the Tract data to the bottom of the plat.
    write_all_tracts(merged)

    merged = merged.convert('RGB')

    # Save the final plat, if output_file was specified.
    if output_file is not None:
        merged.save(output_file)

    return merged


def plat_plss(PLSSDescObj: pyTRS.PLSSDesc, output_file=None):
    """Generate a plat of a parsed PLSSDesc object, optionally saving to
    a .pdf at the specified output filepath `output_file=`, and
    returning a list of .png images of the plats.
    (lots/QQs must be parsed within the Tracts for this to work.)"""

    twps = plss_to_grid(PLSSDescObj)
    tracts = PLSSDescObj.parsedTracts

    # construct a dict to link Tracts to their respective Twps
    all_twps = twps.keys()
    twp_to_tract = {}
    for k in all_twps:
        twp_to_tract[k] = []
    orphan_tracts = []  # Tracts whose T&R isn't found. # TODO: Handle these.
    for tract in tracts:
        TR = tract.twp + tract.rge
        if TR in twp_to_tract.keys():
            twp_to_tract[TR].append(tract)
        else:
            orphan_tracts.append(tract)

    plats = []
    for k, v in twps.items():
        plats.append(plat_twp(v, tracts=twp_to_tract[k]))

    while output_file is not None:
        if not output_file.lower().endswith('.pdf'):
            raise Exception('Error: output_file should end with `.pdf`')
            break
        if len(plats) == 0:
            break
        im1 = plats[0]
        if len(plats) > 0:
            rem_plats = plats[1:]
        else:
            rem_plats = []
        im1.save(output_file, save_all=True, append_images=rem_plats)
        break

    return plats


def plat(text, output_file, config='', launch=False):
    parsed_desc = pyTRS.PLSSDesc(text, config=config, initParseQQ=True)
    plat_plss(parsed_desc, output_file)
    if launch:
        import os
        os.startfile(output_file)

desc_text = 'T154-R97 Sec 14: NE/4, Sec 22: W/2SW, SE/4; T155-R97 Sec 1: Lots 1 - 4, S2N2, T156N-R97W Sections 1 - 36: ALL'
output = r'C:\Users\James Imes\Desktop\tplat_testing.pdf'
plat(desc_text, output, config='n,w', launch=True)