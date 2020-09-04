# Copyright (C) 2020, James P. Imes, all rights reserved.

"""A basic interpreter for parsed PLSSDesc and Tract objects, for
converting them to a grid, and basic platting."""

from pyTRS import pyTRS

# TODO: Handle sections that didn't generate any lots/QQ's (e.g., m&b etc.).

# TODO: Generate a function for importing an entire section's worth of lot definitions
#  (from csv maybe?)

# TODO: Add a kwarg in a lot of places for importing lot_definitions from file.
#  E.g., tracts_into_twp_grids


class TownshipGrid():
    """A single Township/Range, and its 36 sections."""

    # Sections 1-6, 13-18, and 25-30 (inclusive) are east-to-west (i.e. right-to-left)
    # -- all other sections are left-to-right.
    right_to_left_sections = list(range(1, 7)) + list(range(13, 19)) + list(range(25, 31))

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
            if secNum in TownshipGrid.right_to_left_sections:
                y = -secNum % 6
            else:
                y = secNum % 6
            self.sections[secNum] = {
                'coord': (x, y),
                'SectionGrid': SectionGrid.from_TwpRgeSec(
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
        self.sections[int(section_number)]['SectionGrid'].lot_definitions = lot_definitions

    def filled_sections(self):
        x_sec = []
        for secNum, val in self.sections.items():
            if val['SectionGrid'].has_any():
                x_sec.append(val['SectionGrid'])
        return x_sec


class SectionGrid():

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
        self.unhandled_lots = []

        try:
            secNum = int(sec)
        except:
            secNum = 0

        if lot_definitions is None:
            if secNum > 0 and secNum <= 5:
                lot_definitions = SectionGrid.def_LD_01_thru_05
            elif secNum == 6:
                lot_definitions = SectionGrid.def_LD_06
            elif secNum in [7, 18, 30, 31]:
                lot_definitions = SectionGrid.def_LD_07_18_30_31
            else:
                lot_definitions = SectionGrid.def_LD_na

        self.lot_definitions = lot_definitions

        # A dict for the 16 aliquot divisions of a standard section,
        # with (0, 0) being NWNW and (3, 3) being SESE -- i.e. beginning
        # at the NWNW, and running east and south. The nested dict for
        # each QQ contains the x,y coordinates in the grid, and whether
        # that QQ has been included -- i.e. 'val', which is either
        # 0 ('nothing') or 1 ('something') to track whether the QQ
        # (or equivalent Lot) was identified in the tract description.
        self.QQgrid = {
            'NWNW': {'coord': (0, 0), 'val': 0},
            'NENW': {'coord': (1, 0), 'val': 0},
            'NWNE': {'coord': (2, 0), 'val': 0},
            'NENE': {'coord': (3, 0), 'val': 0},
            'SWNW': {'coord': (0, 1), 'val': 0},
            'SENW': {'coord': (1, 1), 'val': 0},
            'SWNE': {'coord': (2, 1), 'val': 0},
            'SENE': {'coord': (3, 1), 'val': 0},
            'NWSW': {'coord': (0, 2), 'val': 0},
            'NESW': {'coord': (1, 2), 'val': 0},
            'NWSE': {'coord': (2, 2), 'val': 0},
            'NESE': {'coord': (3, 2), 'val': 0},
            'SWSW': {'coord': (0, 3), 'val': 0},
            'SESW': {'coord': (1, 3), 'val': 0},
            'SWSE': {'coord': (2, 3), 'val': 0},
            'SESE': {'coord': (3, 3), 'val': 0}
        }

    def lots_by_QQname(self) -> dict:
        """Get a dict, with QQ's as keys, and whose values are each a
        list of the lot(s) that correspond with those QQ's. Note that it
        is possible for more than 1 lot per QQ, so the values are all
        lists."""
        ret_dict = {}
        # TODO: Handle lots whose corresponding aliquots are > QQ (e.g. 'L1' -> 'N2NE')
        #   Need to break these down into QQs.
        for k, v in self.lot_definitions.items():
            if v in ret_dict.keys():
                ret_dict[v].append(k)
            else:
                ret_dict[v] = [k]
        return ret_dict

    def lots_by_grid(self) -> list:
        """Convert the `lot_definitions` into a grid (nested list) of
        which lots fall within which coordinate. For example, 'L1'
        through 'L4' in a standard Section 1 correspond to the N2N2
        QQ's, respectively -- so this method would output a grid whose
        (0,0), (1,0), (2,0), and (3,0) are filled with ['L4'], ['L3'],
        ['L2'], and ['L1'], respectively."""
        lots_by_QQname_dict = self.lots_by_QQname()
        ar = self.output_array()

        for qq_name, dv in self.QQgrid.items():
            x = dv['coord'][0]
            y = dv['coord'][1]
            lots = lots_by_QQname_dict.get(qq_name)
            if lots is not None:
                ar[y][x] = lots
            else:
                ar[y][x] = []

        return ar

    @staticmethod
    def from_TwpRgeSec(twp='', rge='', sec='', defaultNS='n', defaultEW='w',
                       lot_definitions=None):
        """Construct a SectionGrid with Twp, Rge, and Section separately."""
        if isinstance(twp, int):
            twp = str(twp) + defaultNS
        if isinstance(rge, int):
            rge = str(rge) + defaultEW
        if isinstance(sec, int):
            sec = str(sec).rjust(2, '0')

        trs = twp + rge + sec

        return SectionGrid(trs, lot_definitions=lot_definitions)

    @staticmethod
    def from_tract(TractObj : pyTRS.Tract, lot_definitions=None):
        """Create a SectionGrid object from a pyTRS.Tract object and
        incorporate the lotList and QQList."""
        twp, rge, sec = TractObj.twp, TractObj.rge, TractObj.sec
        secObj = SectionGrid.from_TwpRgeSec(twp, rge, sec, lot_definitions=lot_definitions)
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
                self.unhandled_lots.append(lot)
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

    def output_plat(self, include_header=False) -> str:
        """Output a plat (as a string) of the Section grid values."""

        ar = self.output_array()
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

        return (header + '\n') * include_header + plat_txt

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
        # in the SectionGrid.QQgrid (which is 4x4 in a standard section).
        ar = [[0 for _a in range(max_x + 1)] for _b in range(max_y + 1)]

        for qq in self.QQgrid.values():
            x = qq['coord'][0]
            y = qq['coord'][1]
            if qq['val'] != 0:
                ar[y][x] = qq['val']

        return ar

    def filled_coords(self) -> list:
        """Return a list of coordinates in the SectionGrid that are filled."""
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


def plss_to_grids(PLSSDescObj: pyTRS.PLSSDesc) -> dict:
    """Generate a dict of TownshipGrid objectss (keyed by T&R
    '000x000y') from a parsed PLSSDesc object."""
    tl = PLSSDescObj.parsedTracts

    return tracts_into_twp_grids(tl)


def tracts_into_twp_grids(tract_list, grid_dict=None) -> dict:
    """Incorporate a list of parsed Tract objects into TownshipGrid
    objects, and return a dict of those TownshipGrids (keyed by T&R). If
    `grid_dict` is specified, it will be updated and returned. If not, a
    new one will be created and returned."""
    if grid_dict is None:
        grid_dict = {}

    # We'll incorporate each Tract object into a SectionGrid object. If necessary,
    # we'll first create TownshipGrid objects that do not yet exist in the grid_dict.
    for tractObj in tract_list:
        twp, rge, sec = pyTRS.break_trs(tractObj.trs)
        # TODO: handle error parses ('TRerr' / 'secError').

        if twp + rge not in grid_dict.keys():
            # If a TownshipGrid object does not yet exist for this T&R in the dict,
            # create one, and add it to the dict now.
            grid_dict[twp + rge] = TownshipGrid(twp=twp, rge=rge)

        # Now incorporate the Tract object into a SectionGrid object within the dict.
        # No /new/ SectionGrid objects are created at this point (since a TownshipGrid
        # object creates all 36 of them at init), but SectionGrid objects are
        # updated at this point to incorporate our tracts.
        grid_dict[twp + rge].sections[int(sec)]['SectionGrid'].incorporate_tract(tractObj)

    return grid_dict


def filter_tracts_by_tr(tract_list, tr_dict=None) -> dict:
    """Filter Tract objects into a dict, keyed by T&R (formatted
    '000x000y', or fewer digits)."""
    # construct a dict to link Tracts to their respective Twps
    if tr_dict is None:
        tr_dict = {}
    tr_to_tract = {}

    # Copy the twp_dict to twp_to_tract
    for twp_key, twp_val in tr_dict.keys():
        tr_to_tract[twp_key] = twp_val

    # Sort each Tract object in the tract_list into the new dict, alongside the
    # old data (if any).
    for tract in tract_list:
        TR = tract.twp + tract.rge
        if 'TRerr' in TR:
            TR = 'TRerr'
        if TR in tr_to_tract.keys():
            tr_to_tract[TR].append(tract)
        else:
            tr_to_tract[TR] = [tract]

    return tr_to_tract