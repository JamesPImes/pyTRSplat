# Copyright (C) 2020, James P. Imes, all rights reserved.

"""
Misc tools and utils that do not belong in other packages.
"""


########################################################################
# Sorting pyTRS.Tracts by Twp/Rge.
########################################################################

def filter_tracts_by_twprge(tract_list, twprge_dict=None) -> dict:
    """
    Filter pyTRS.Tract objects into a dict, keyed by T&R (formatted
    '000x000y', or fewer digits).
    """
    from pyTRS import PLSSDesc

    # If the user passes a PLSSDesc object, pull its TractList obj.
    if isinstance(tract_list, PLSSDesc):
        tract_list = tract_list.parsedTracts

    # construct a dict to link Tracts to their respective Twps
    if twprge_dict is None:
        twprge_dict = {}
    twprge_to_tract = {}

    # Copy the twp_dict to twp_to_tract
    for twp_key, twp_val in twprge_dict.items():
        twprge_to_tract[twp_key] = twp_val

    # Sort each Tract object in the tract_list into the new dict, alongside the
    # old data (if any).
    for tract in tract_list:
        twprge = tract.twp + tract.rge
        if 'TRerr' in twprge:
            twprge = 'TRerr'
        if twprge == '':
            twprge = 'undef'
        twprge_to_tract.setdefault(twprge, [])
        twprge_to_tract[twprge].append(tract)

    return twprge_to_tract


########################################################################
# Misc. tools for (re)formatting lots and QQs
########################################################################

def _smooth_QQs(aliquot_text) -> list:
    """
    Ensure the input aliquot text is in a list of properly formatted
    QQ's. (Expects already-parsed data that consists only of standard
    aliquot divisions -- e.g., 'NENE' or 'N2NE' or 'S½SE¼' or 'ALL',
    etc.).
        ex: 'N2NE' -> ['NENE', 'NWNE']
        ex: 'NENE' -> ['NENE']
        ex: 'S2NENE' -> ['NENE']
    NOTE: Does NOT convert lots to QQ.
    """
    import pyTRS.pyTRS

    qq_l = []
    for aliq in aliquot_text.replace(' ', '').split(','):
        scrubbed = pyTRS.pyTRS.scrub_aliquots(aliq, cleanQQ=True)
        scrubbed = pyTRS.pyTRS.unpack_aliquots(scrubbed)
        for qq in scrubbed:
            # Append only the last 4 chars (ie. the true QQ: 'S2NENE' -> 'NENE')
            qq_l.append(qq[-4:])
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
    except:
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
