# Copyright (C) 2020, James P. Imes, all rights reserved.

"""A basic interpreter for parsed PLSSDesc and Tract objects, for
converting them to a grid, and basic platting."""

from pyTRS import pyTRS

# TODO: Handle sections that didn't generate any lots/QQ's (e.g., m&b etc.).

# TODO: Add a kwarg in a lot of places for importing lot_definitions from file.
#  E.g., tracts_into_twp_grids


class TownshipGrid:
    """A grid of a single Township/Range, containing also a grid for
    each of its 36 sections (SectionGrid objects). At init, use `tld=`
    to pass in a TwpLotDefinitions object to optionally define lots to
    corresponding QQ's in respective sections."""

    # Sections 1-6, 13-18, and 25-30 (inclusive) are east-to-west (i.e. right-to-left)
    # -- all other sections are left-to-right.
    right_to_left_sections = list(range(1, 7)) + list(range(13, 19)) + list(range(25, 31))

    def __init__(self, twp='', rge='', tld='default'):

        # NOTE: `tld` stands for `TwpLotDefinitions`

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
                'SectionGrid': SectionGrid(sec=secNum, twp=twp, rge=rge)
            }

        if tld == 'default':
            default_tld = TwpLotDefinitions([list(range(1,37))])
            self.apply_TwpLotDefs(default_tld)
        elif tld is not None:
            self.apply_TwpLotDefs(tld)

    def apply_TwpLotDefs(self, tld):
        """Apply a TwpLotDefinitions object (i.e. set the respective
        SectionGrid's LotDefinitions objects)."""
        if not isinstance(tld, TwpLotDefinitions):
            raise TypeError('`tld` must be `TwpLotDefinitions` object.')
        for key, val in tld.items():
            self.apply_LotDefs(key, val)

    def apply_LotDefs(self, section_number : int, ld):
        if not isinstance(ld, LotDefinitions):
            raise TypeError('`ld` must be type `LotDefinitions`')
        self.sections[int(section_number)]['SectionGrid'].lot_definitions = ld

    def filled_sections(self):
        """Return a list of SectionGrid objects that have at least one QQ filled."""
        x_sec = []
        for secNum, val in self.sections.items():
            if val['SectionGrid'].has_any():
                x_sec.append(val['SectionGrid'])
        return x_sec


class LotDefinitions(dict):
    """A dict object for defining which lots correspond to which QQ in a
    given section. At init, pass in an int 1 - 36 (inclusive) to set to
    the /default/ for that section in a STANDARD township, or pass a
    properly formatted dict to convert it to a LotDefinitions object."""

    # Some defaults for sections in a 'standard' 6x6 Township grid.
    # (Sections along the north and west boundaries of the township have
    # 'expected' lot locations. In practice, these will RARELY be the
    # only lots in a township, and they are not always consistent, even
    # within these sections. Even so, it is better than nothing.)

    DEF_01_to_05 = {
        'L1': 'NENE',
        'L2': 'NWNE',
        'L3': 'NENW',
        'L4': 'NWNW'
    }

    DEF_06 = {
        'L1': 'NENE',
        'L2': 'NWNE',
        'L3': 'NENW',
        'L4': 'NWNW',
        'L5': 'SWNW',
        'L6': 'NWSW',
        'L7': 'SWSW',
    }

    DEF_07_18_30_31 = {
        'L1': 'NWNW',
        'L2': 'SWNW',
        'L3': 'NWSW',
        'L4': 'SWSW'
    }

    # All other sections in a /standard/ Twp have no lots.
    DEF_00 = {}

    def __init__(self, default=None):
        super().__init__()
        if isinstance(default, dict):
            self.absorb_dict(default)
        elif default in [1, 2, 3, 4, 5]:
            self.absorb_dict(LotDefinitions.DEF_01_to_05)
        elif default == 6:
            self.absorb_dict(LotDefinitions.DEF_06)
        elif default in [7, 18, 30, 31]:
            self.absorb_dict(LotDefinitions.DEF_07_18_30_31)
        else:
            self.absorb_dict(LotDefinitions.DEF_00)

    def set_lot(self, lot, definition):
        """Set definition (value) to lot (key). Overwrite, if already
        exists. Using this method ensures that the resulting format will
        be as expected elsewhere in the program (assuming input format
        is acceptable)."""

        # If no leading 'L' was fed in, add it now (e.g. 1 -> 'L1')
        if str(lot).upper()[0] != 'L':
            lot = 'L' + str(lot).upper()

        # Ensure the definitions are broken down into QQ's by passing them
        # through pyTRS.Tract parsing, and pulling the resulting QQList.
        qq_list = pyTRS.Tract(desc=definition, initParseQQ=True, config='cleanQQ').QQList
        self[lot] = ','.join(qq_list)

    def absorb_dict(self, dct):
        """Absorb another LotDefinitions object or appropriately
        formatted dict. Will overwrite existing keys, if any. Using this
        method ensures that the resulting format will be as expected
        elsewhere in the program (assuming input format is acceptable)."""
        for lot, definition in dct.items():
            self.set_lot(lot, definition)

    def lots_by_QQname(self) -> dict:
        """Get a dict, with QQ's as keys, and whose values are each a
        list of the lot(s) that correspond with those QQ's. Note that it
        is possible for more than 1 lot per QQ, so the values are all
        lists."""
        ret_dict = {}
        for k, v in self.items():
            list_of_qqs = _smooth_QQs(v)
            for qq in list_of_qqs:
                if qq in ret_dict.keys():
                    ret_dict[qq].append(k)
                else:
                    ret_dict[qq] = [k]
        return ret_dict


class TwpLotDefinitions(dict):
    """A dict of LotDefinition objects (i.e. a nested dict) for an
    entire township. Each key is a section number (an int), whose value
    is a LotDefinition object for that section. If a section number or
    list of section numbers (all ints) are passed at init, will use
    default definitions for those sections."""

    def __init__(self, default_sections=None):
        super().__init__()
        for i in range(1,37):
            # Initialize an empty dict for each of the 36 sections in a
            # standard Twp.
            self[i] = LotDefinitions(None)

            # If we want to use_defaults, do so now.
            if isinstance(default_sections, int):
                self[default_sections] = LotDefinitions(default_sections)
            elif isinstance(default_sections, list):
                for sec in default_sections:
                    self[sec] = LotDefinitions(sec)

    def set_section(self, sec_num: int, lot_defs: LotDefinitions):
        self[sec_num] = lot_defs

    @staticmethod
    def from_csv(fp, twp=None, rge=None):
        """Generate a TwpLotDefinitions object from a properly formatted
        csv file at filepath `fp`. Specify `twp=<str>` and `rge=<str>`
        for which rows should match -- ex. ... twp='154n', rge='97w'.
        (See documentation for how to format .csv files.)"""

        # Confirm that `fp` points to an existing csv file. If not,
        # return None.
        if not confirm_file(fp, '.csv'):
            return None

        tld = TwpLotDefinitions()
        if None in [twp, rge]:
            return tld

        twp = twp.lower()
        rge = rge.lower()

        import csv
        f = open(fp, 'r')
        reader = csv.DictReader(f)

        for row in reader:
            csv_twp, csv_rge = row['twp'].lower(), row['rge'].lower()
            if csv_twp == twp and csv_rge == rge:
                # If this row matches our twp and rge, set the lot to our tld.
                tld[int(row['sec'])].set_lot(row['lot'], row['qq'])

        return tld


class LotDefDB(dict):
    """A dict database of TwpLotDefinitions, whose keys are T&R (formatted
    '000x000y' or fewer digits), and each whose values is a
    TwpLotDefinitions object for that T&R."""

    def __init__(self):
        super().__init__()

    @staticmethod
    def from_csv(fp):
        """Generate a LDDatabase of TwpLotDefinitions objects from a
        properly formatted file at filepath `fp`. Converts each unique
        T&R in the .csv file into a separate TwpLotDefinitions object.
        Returns a dict, keyed by T&R (formatted '000x000y' or fewer
        digits), each of whose value is the TwpLotDefinitions object for
        that T&R.  (See documentation for how to format .csv files.)"""

        # Confirm that `fp` points to an existing csv file. If not,
        # return None.
        if not confirm_file(fp, '.csv'):
            return None

        ldd = LotDefDB()

        import csv
        f = open(fp, 'r')
        reader = csv.DictReader(f)

        for row in reader:
            twp, rge = row['twp'].lower(), row['rge'].lower()
            sec = int(row['sec'])
            lot, qq = row['lot'], row['qq']
            # If now TLD has yet been created for this T&R, do it now.
            ldd.setdefault(twp + rge, TwpLotDefinitions())

            # Add this lot/qq definition for the section/twp/rge on this row.
            ldd[twp + rge][sec].set_lot(lot, qq)

        return ldd

    def set_twp(self, twprge, twplotdef_obj):
        self[twprge] = twplotdef_obj

    def trs(self, trs):
        """Access the (section-level) LotDefinitions object for the
        specified `trs`. Returns either the corresponding LotDefinitions
        object -- or None, if none was found."""
        twp, rge, sec = pyTRS.break_trs(trs)
        if twp+rge not in self.keys():
            return None
        try:
            return self[twp+rge][int(sec)]
        except:
            return None


class SectionGrid:
    """A grid of a single Section, divided into standard PLSS aliquot
    quarter-quarters (QQs) -- i.e. 4x4 for a standard section.
    Takes optional `ld` argument for specifying LotDefinitions object
    (defaults to 'standard' township layout if not specified)."""

    def __init__(self, sec='', twp='', rge='', ld='default'):

        # Note: twp and rge should have their direction specified
        #   ('n' or 's' for twp; and 'e' or 'w' for rge). Without doing
        #   so, various functionality may break.

        twp = twp.lower()
        rge = rge.lower()
        self.twp = twp
        self.rge = rge

        # Ensure sec is formatted as a two digit string -- ex: '01'
        sec = str(int(sec)).rjust(2, '0')

        self.sec = sec
        self.tr = twp+rge
        self.trs = f"{twp}{rge}{sec}".lower()
        self.unhandled_lots = []

        try:
            secNum = int(sec)
        except:
            secNum = 0

        self.lot_definitions = {}
        if ld == 'default':
            self.lot_definitions = LotDefinitions(secNum)
        elif isinstance(ld, LotDefinitions):
            self.lot_definitions = ld
        else:
            self.lot_definitions = LotDefinitions(None)

        # A dict for the 16 aliquot divisions of a standard section,
        # with (0, 0) being NWNW and (3, 3) being SESE -- i.e. beginning
        # at the NWNW, and running east and south. The nested dict for
        # each QQ contains the x,y coordinates in the grid, and whether
        # that QQ has been switched `on` -- i.e. 'val', which is either
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

    @staticmethod
    def from_trs(trs='', ld='default'):
        """Create and return a SectionGrid object by passing in a TRS
        (e.g., '154n97w14'), rather than the separate Sec, Twp, Rge
        components. Also takes optional `ld` argument for specifying
        LotDefinitions object."""
        twp, rge, sec = pyTRS.break_trs(trs)
        return SectionGrid(sec, twp, rge, ld)

    def apply_lddb(self, lddb):
        """Apply the appropriate LotDefinitions object from a LotDefsDB
        object, if one exists. Will not overwrite anything if no
        LotDefinitions object exists for this section in the LDDB."""
        ld = lddb.trs(self.trs)
        if ld is not None:
            self.lot_definitions = ld

    def apply_TwpLotDefs(self, tld):
        """Apply the appropriate LotDefinitions object from a
        TwpLotDefinitions object, if one exists. Will not overwrite
        anything if no LotDefinitions object exists for this section in
        the TwpLotDefinitions."""
        ld = tld.get(int(self.sec), None)
        if ld is not None:
            self.lot_definitions = ld

    def lots_by_QQname(self) -> dict:
        """Get a dict, with QQ's as keys, and whose values are each a
        list of the lot(s) that correspond with those QQ's. Note that it
        is possible for more than 1 lot per QQ, so the values are all
        lists."""

        # This functionality is handled by LotDefinitions object.
        return self.lot_definitions.lots_by_QQname()

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
    def from_tract(TractObj : pyTRS.Tract, ld='default'):
        """Create a SectionGrid object from a pyTRS.Tract object and
        incorporate the lotList and QQList."""
        twp, rge, sec = TractObj.twp, TractObj.rge, TractObj.sec
        secObj = SectionGrid(sec=sec, twp=twp, rge=rge, ld=ld)
        secObj.incorporate_tract(TractObj)

        return secObj

    def incorporate_tract(self, TractObj : pyTRS.Tract):
        """Check the lotList and QQList of a parsed pyTRS.Tract object,
        and incorporate any hits into the grid."""
        self.incorporate_QQList(TractObj.QQList)
        self.incorporate_lotList(TractObj.lotList)

    def incorporate_lotList(self, lotList : list):
        """Incorporate all lots in the lotList into the grid."""
        # QQ equivalents to Lots
        equiv_qq = []

        # Convert each lot to its equivalent QQ, per the lot_definitions, and
        # add them to the equiv_qq list.
        for lot in lotList:
            # First remove any divisions in the lot (e.g., 'N2 of L1' -> 'L1')
            lot = _lot_without_div(lot)

            eq_qqs_from_lot = self._unpack_ld(lot)
            if eq_qqs_from_lot is None:
                self.unhandled_lots.append(lot)
                continue
            equiv_qq.extend(eq_qqs_from_lot)

        self.incorporate_QQList(equiv_qq)

    def incorporate_QQList(self, QQList : list):
        """Incorporate all QQs in the QQList into the grid."""

        # `qq` can be fed in as 'NENE' or 'NENE,NWNE'. So we need to break it
        # into components before incorporating.
        for qq in QQList:
            for qq_ in qq.replace(' ', '').split(','):
                self.QQgrid[qq_]['val'] = 1

    def _unpack_ld(self, lot) -> list:
        """Pass a lot number (string 'L1' or int 1), and get a list of the
        corresponding / properly formatted QQ(s) from the
        `.lot_definitions` of this SectionGrid object. Returns None if
        the lot is undefined, or defined with invalid QQ's."""

        equiv_aliquots = []
        # Cull lot divisions (i.e. 'N2 of L1' to just 'L1')
        lot = _lot_without_div(lot)

        # Get the raw definition from the LotDefinitions object.
        # If undefined in the LD obj, return None.
        raw_ldef = self.lot_definitions.get(lot, None)
        if raw_ldef is None:
            return None

        # Ensure the raw lot definition is in the expected format and is
        # broken out into QQ chunks (e.g., a 'L1' that is defined as
        # 'N2NE4' should be converted to 'NENE' and 'NWNE').  And add
        # the resulting QQ(s) to the list of aliquots.
        equiv_aliquots.extend(_smooth_QQs(raw_ldef))

        if len(equiv_aliquots) == 0:
            return None

        return equiv_aliquots

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
        """Convert the grid to an array (oriented from NWNW to SESE)"""

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


def plss_to_grids(PLSSDescObj: pyTRS.PLSSDesc, lddb=None) -> dict:
    """Generate a dict of TownshipGrid objectss (keyed by T&R
    '000x000y') from a parsed PLSSDesc object."""
    tl = PLSSDescObj.parsedTracts
    return tracts_into_twp_grids(tl, lddb=lddb)


def tracts_into_twp_grids(tract_list, grid_dict=None, lddb=None) -> dict:
    """Incorporate a list of parsed Tract objects into TownshipGrid
    objects, and return a dict of those TownshipGrids (keyed by T&R). If
    `grid_dict` is specified, it will be updated and returned. If not, a
    new one will be created and returned."""
    if grid_dict is None:
        grid_dict = {}

    # If lddb (LotDefDB) is not specified, create a default.
    if lddb is None:
        lddb = LotDefDB()

    # We'll incorporate each Tract object into a SectionGrid object. If necessary,
    # we'll first create TownshipGrid objects that do not yet exist in the grid_dict.
    for tractObj in tract_list:
        twp, rge, sec = pyTRS.break_trs(tractObj.trs)
        # TODO: handle error parses ('TRerr' / 'secError').

        # Get the TLD for this T&R from the lddb, if one exists. If not,
        # create and use a default TLD object.
        tld = lddb.get(twp + rge, TwpLotDefinitions())

        # If a TownshipGrid object does not yet exist for this T&R in the dict,
        # create one, and add it to the dict now.
        grid_dict.setdefault(twp + rge, TownshipGrid(twp=twp, rge=rge, tld=tld))

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


def confirm_file(fp, extension=None) -> bool:
    """Check if `fp` is a filepath to an existing file. Optionally also
    confirm whether that file has the specified extension (must include
    the period -- ex: '.csv')."""

    import os
    try:
        if not os.path.isfile(fp):
            return False
    except:
        return False

    if extension is None:
        return True

    # If extension was specified, confirm the fp ends in such.
    return os.path.splitext(fp)[1].lower() == extension.lower()


########################################################################
# Misc. tools for formatting / reformatting lots and QQs
########################################################################

def _smooth_QQs(aliquot_text) -> list:
    """Ensure the input aliquot text is in a list of properly formatted
    QQ's. (Expects already parsed data that consists only of standard
    aliquot divisions -- e.g., 'NENE' or 'N2NE' or 'S½SE¼' or 'ALL',
    etc.)  Does NOT convert lots to QQ."""
    qq_l = []
    for aliq in aliquot_text.replace(' ', '').split(','):
        scrubbed = pyTRS.scrub_aliquots(aliq, cleanQQ=True)
        qq_l.extend(pyTRS.unpack_aliquots(scrubbed))
    return qq_l


def _lot_without_div(lot) -> str:
    """Cull lot divisions.
        ex: 'N2 of L1' -> 'L1'"""
    # If only an int is fed in, return it as a formatted lot str
    # (i.e. 1 -> 'L1')
    if isinstance(lot, int):
        return f"L{lot}"
    return lot.split(' ')[-1].upper()


def _lot_without_L(lot) -> str:
    """Cull leading 'L' from lot.  Also cull lot divisions, if any.
        ex: 'N2 of L1' -> '1'"""
    lot = _lot_without_div(lot)
    return lot.replace('L', '')
