# Copyright (C) 2020, James P. Imes, all rights reserved.

"""
Misc tools and utils that do not belong in other packages.
"""


########################################################################
# Misc. tools for (re)formatting lots and QQs
########################################################################

def _smooth_QQs(aliquot_text) -> list:
    """
    INTERNAL USE:

    Ensure the input aliquot text is in a list of properly formatted
    QQ's. (Expects already-parsed data that consists only of standard
    aliquot divisions -- e.g., 'NENE' or 'N2NE' or 'S½SE¼' or 'ALL',
    etc.).
        ex: 'N2NE' -> ['NENE', 'NWNE']
        ex: 'NENE' -> ['NENE']
        ex: 'S2NENE' -> ['NENE']
    NOTE: Does NOT convert lots to QQ.
    """
    from pytrs import Tract

    qq_l = []
    for aliq in aliquot_text.replace(' ', '').split(','):
        tract = Tract(aliq, config='clean_qq, qq_depth.2', parse_qq=True)
        qq_l.extend(tract.qqs)
    return qq_l


def _lot_without_div(lot) -> str:
    """Cull lot divisions and return a clean lot name.
        ex: 'N2 of L1' -> 'L1'
        ex: 1 -> 'L1'"""
    # If only an int is fed in, return it as a formatted lot str
    # (i.e. 1 -> 'L1')
    if isinstance(lot, int):
        return f"L{lot}"
    return lot.split(' ')[-1].upper()


def _simplify_lot_number(lot) -> str:
    """Cull leading 'L' from lot name.  Also cull lot divisions, if any.
    Returns a numeric-only string.
        ex: 'N2 of L1' -> '1'
        ex: 'L1' -> '1'"""
    lot = _lot_without_div(lot)
    return lot.replace('L', '')


########################################################################
# Other
########################################################################

def confirm_file(fp, extension=None) -> bool:
    """
    Check if `fp` is a filepath to an existing file. Optionally also
    confirm whether that file has the specified extension (must include
    the leading period -- ex: '.csv').
    """

    from pathlib import Path
    try:
        if not Path(fp).is_file():
            return False
    except TypeError:
        return False

    if extension is None:
        return True

    # If extension was specified, confirm the fp ends in such.
    return Path(fp).suffix.lower() == extension.lower()


def confirm_file_ext(fp, extension) -> bool:
    """
    Check if `fp` is a filepath ending in `extension` (must include
    the leading period for `extension` -- ex: '.csv').
    """

    from pathlib import Path
    return Path(fp).suffix.lower() == extension.lower()


def cull_list(
        list_to_cull: list, desired_indices: list) -> list:
    """
    Take a list, and return a list of the same objects, but limited to
    the `desired_indices`. Discards any page requests that do not exist
    (i.e. below 0 or above the last index in `list_to_cull`). If
    `desired_indices` is None, will return a copy of the original list
    (i.e. all pages).

    :param list_to_cull: Any list
    :param desired_indices: A list of indexes (integers) to pull
    from the `list_to_cull`.
    :return: Returns a new list of only the desired pages (but the
    objects in the list have not been copied.)
    """

    if desired_indices is None:
        # If not specified, return an entire copy of the original list
        return list_to_cull.copy()
    elif isinstance(desired_indices, int):
        desired_indices = [desired_indices]
    else:
        desired_indices = list(desired_indices)

    output_list = []
    for page_num in desired_indices:
        if page_num >= len(list_to_cull) or page_num < 0:
            pass
        else:
            output_list.append(list_to_cull[page_num])
    return output_list


########################################################################
# Deprecated pytrs functions. Use of these in this library should be
# refactored to use pytrs.TRS objects at some point.
########################################################################

def break_trs(trs: str) -> tuple:
    """
    Break down a TRS that is already in the format '000n000w00' (or
    fewer digits for twp/rge) into its component parts.
    Returns a 3-tuple containing:
    -- a str for `twp`
    -- a str for `rge`
    -- either a str or None for `sec`

        ex:  '154n97w14' -> ('154n', '97w', '14')
        ex:  '154n97w' -> ('154n', '97w', None)
        ex:  '154n97wXX' -> ('154n', '97w', 'XX')
        ex:  'XXXzXXXz14' -> ('XXXz', 'XXXz', '14')
        ex:  'asdf' -> ('XXXz', 'XXXz', 'XX')

    NOTE: This function is being deprecated. Better to use ``pytrs.TRS``
    objects instead.
    """

    from pytrs import TRS

    trs = TRS(trs)
    sec = trs.sec
    if not trs.sec_num:
        sec = None

    return trs.twp, trs.rge, sec


def decompile_twprge(twprge) -> tuple:
    """
    Take a compiled T&R (format '000n000w', or fewer digits) and break
    it into four elements, returned as a 4-tuple:
    (Twp number, Twp direction, Rge number, Rge direction)
        NOTE: If Twp and Rge cannot be matched, will return the error
        versions of Twp/Rge:
            ('XXXz', None, 'XXXz', None)
        ... or the undefined versions:
            ('___z', None, '___z', None)
        ex: '154n97w'   -> ('154', 'n', '97', 'w')
        ex: 'asdf'      -> ('XXXz', None, 'XXXz', None)
        ex: ''          -> ('___z', None, '___z', None)

    NOTE: This function is being deprecated. Better to use ``pytrs.TRS``
    objects instead.
    """

    from pytrs.parser.parser import TRS

    trs = TRS(twprge)
    twp_num = trs.twp_num
    if not trs.twp_num:
        twp_num = trs.twp

    rge_num = trs.rge_num
    if not trs.rge_num:
        rge_num = trs.rge

    return str(twp_num), trs.twp_ns, str(rge_num), trs.rge_ew