from pathlib import Path

try:
    from pytrsplat import PlatGroup, Settings
    from ._utils import (
        prepare_settings,
        get_test_settings_for_plat,
        images_match,
        image_matches_existing,
        add_docstring,
        write_if_new_group,
        gen_all_test_plats,
        RESOURCES_DIR,
        TEST_RESULTS_DIR,
    )

except ImportError:
    import sys

    sys.path.append('../')
    from pytrsplat import PlatGroup, Settings
    from _utils import (
        prepare_settings,
        get_test_settings_for_plat,
        images_match,
        image_matches_existing,
        add_docstring,
        write_if_new_group,
        gen_all_test_plats,
        RESOURCES_DIR,
        TEST_RESULTS_DIR,
    )

__all__ = [
    'FILENAME_TO_GENFUNC',
    'platgroup2tracts1twprge_nodefaults',
    'platgroup2tracts2twprges_nodefaults',
    'platgroup2tracts2twprges_lotnums_defaults40ac',
    'platgroup2tracts2twprges_lotnums_defaults80ac',
    'platgroup2tracts_defaults40ac',
    'platgroup2tracts_defaults80ac',
    'platgroup2tracts_lotnums_defaults40ac',
    'platgroup2tracts_lotnums_defaults80ac',
    'platgroup2tracts_writetracts',
    'platgroup2tracts_writetracts_lotnums',
    'plat3tracts_writetracts_2written',
]

DEFAULT_OUT_DIR = RESOURCES_DIR / 'expected_images' / 'platgroup'
DESC_1 = 'T154N-R97W Sec 1: Lots 1, 2, S/2N/2'
DESC_2 = 'T154N-R97W Sec 6: Lots 2 - 4'
DESC_3 = 'T154N-R96W Sec 8: N/2S/2NW/4'
DESC_4 = 'T154N-R97W Sec 12: NE/4'


@add_docstring(
    'PlatGroup - Two tracts, one Twp/Rge. No default lots.',
    DESC_1, DESC_2)
def platgroup2tracts1twprge_nodefaults(fn: str, out_dir: Path = DEFAULT_OUT_DIR, override=False):
    settings = get_test_settings_for_plat()
    pg = PlatGroup(settings=settings)
    pg.add_description(DESC_1)
    pg.add_description(DESC_2)
    pg.execute_queue()
    return write_if_new_group(out_dir / fn, pg, override)


@add_docstring(
    'PlatGroup - Two tracts, two Twp/Rge. No default lots.',
    DESC_1, DESC_3)
def platgroup2tracts2twprges_nodefaults(fn: str, out_dir: Path = DEFAULT_OUT_DIR, override=False):
    settings = get_test_settings_for_plat()
    pg = PlatGroup(settings=settings)
    pg.add_description(DESC_1)
    pg.add_description(DESC_3)
    pg.execute_queue()
    return write_if_new_group(out_dir / fn, pg, override)


@add_docstring(
    'PlatGroup - Two tracts, one Twp/Rge. 40-acre default lots (written).',
    DESC_1, DESC_3)
def platgroup2tracts2twprges_lotnums_defaults40ac(fn: str, out_dir: Path = DEFAULT_OUT_DIR, override=False):
    settings = get_test_settings_for_plat()
    settings.write_lot_numbers = True
    pg = PlatGroup(settings=settings)
    pg.lot_definer.allow_defaults = True
    pg.lot_definer.standard_lot_size = 40
    pg.add_description(DESC_1)
    pg.add_description(DESC_3)
    pg.execute_queue()
    return write_if_new_group(out_dir / fn, pg, override)


@add_docstring(
    'PlatGroup - Two tracts, two Twp/Rge. 80-acre default lots (written).',
    DESC_1, DESC_3)
def platgroup2tracts2twprges_lotnums_defaults80ac(fn: str, out_dir: Path = DEFAULT_OUT_DIR, override=False):
    settings = get_test_settings_for_plat()
    settings.write_lot_numbers = True
    pg = PlatGroup(settings=settings)
    pg.lot_definer.allow_defaults = True
    pg.lot_definer.standard_lot_size = 80
    pg.add_description(DESC_1)
    pg.add_description(DESC_3)
    pg.execute_queue()
    return write_if_new_group(out_dir / fn, pg, override)


@add_docstring(
    'PlatGroup - Two tracts. 40-acre default lots (not written).',
    DESC_1, DESC_2)
def platgroup2tracts_defaults40ac(fn: str, out_dir: Path = DEFAULT_OUT_DIR, override=False):
    settings = get_test_settings_for_plat()
    pg = PlatGroup(settings=settings)
    pg.lot_definer.allow_defaults = True
    pg.lot_definer.standard_lot_size = 40
    pg.add_description(DESC_1)
    pg.add_description(DESC_2)
    pg.execute_queue()
    return write_if_new_group(out_dir / fn, pg, override)


@add_docstring(
    'PlatGroup - Two tracts. 80-acre default lots (not written).',
    DESC_1, DESC_2)
def platgroup2tracts_defaults80ac(fn: str, out_dir: Path = DEFAULT_OUT_DIR, override=False):
    settings = get_test_settings_for_plat()
    pg = PlatGroup(settings=settings)
    pg.lot_definer.allow_defaults = True
    pg.lot_definer.standard_lot_size = 80
    pg.add_description(DESC_1)
    pg.add_description(DESC_2)
    pg.execute_queue()
    return write_if_new_group(out_dir / fn, pg, override)


@add_docstring(
    'PlatGroup - Two tracts. 40-acre default lots (written).',
    DESC_1, DESC_2)
def platgroup2tracts_lotnums_defaults40ac(fn: str, out_dir: Path = DEFAULT_OUT_DIR, override=False):
    settings = get_test_settings_for_plat()
    settings.write_lot_numbers = True
    pg = PlatGroup(settings=settings)
    pg.lot_definer.allow_defaults = True
    pg.lot_definer.standard_lot_size = 40
    pg.add_description(DESC_1)
    pg.add_description(DESC_2)
    pg.execute_queue()
    return write_if_new_group(out_dir / fn, pg, override)


@add_docstring(
    'PlatGroup - Two tracts. 80-acre default lots (written).',
    DESC_1, DESC_2)
def platgroup2tracts_lotnums_defaults80ac(fn: str, out_dir: Path = DEFAULT_OUT_DIR, override=False):
    settings = get_test_settings_for_plat()
    settings.write_lot_numbers = True
    pg = PlatGroup(settings=settings)
    pg.lot_definer.allow_defaults = True
    pg.lot_definer.standard_lot_size = 80
    pg.add_description(DESC_1)
    pg.add_description(DESC_2)
    pg.execute_queue()
    return write_if_new_group(out_dir / fn, pg, override)


@add_docstring(
    'PlatGroup - Two tracts. Tracts written in footer. No default lots.',
    DESC_1, DESC_2)
def platgroup2tracts_writetracts(fn: str, out_dir: Path = DEFAULT_OUT_DIR, override=False):
    settings = get_test_settings_for_plat()
    settings.write_tracts = True
    pg = PlatGroup(settings=settings)
    pg.add_description(DESC_1)
    pg.add_description(DESC_2)
    pg.execute_queue()
    return write_if_new_group(out_dir / fn, pg, override)


@add_docstring(
    'PlatGroup - Two tracts. Tracts written to footer. 40-acre default lots (written).',
    DESC_1, DESC_2)
def platgroup2tracts_writetracts_lotnums(
        fn: str, out_dir: Path = DEFAULT_OUT_DIR, override=False):
    settings = get_test_settings_for_plat()
    settings.write_tracts = True
    settings.write_lot_numbers = True
    pg = PlatGroup(settings=settings)
    pg.lot_definer.allow_defaults = True
    pg.lot_definer.standard_lot_size = 40
    pg.add_description(DESC_1)
    pg.add_description(DESC_2)
    pg.execute_queue()
    return write_if_new_group(out_dir / fn, pg, override)


@add_docstring(
    'PlatGroup - Three tracts. Tracts written to footer (except 3rd due to margin).',
    DESC_1, DESC_2, DESC_4)
def plat3tracts_writetracts_2written(
        fn: str, out_dir: Path = DEFAULT_OUT_DIR, override=False):
    settings = get_test_settings_for_plat()
    settings.write_tracts = True
    pg = PlatGroup(settings=settings)
    pg.lot_definer.allow_defaults = True
    pg.lot_definer.standard_lot_size = 40
    pg.add_description(DESC_1)
    pg.add_description(DESC_2)
    pg.add_description(DESC_4)
    pg.execute_queue()
    return write_if_new_group(out_dir / fn, pg, override)


# Create a dict of .png filenames and their corresponding func, for all funcs.
exclude = (
    'FILENAME_TO_GENFUNC',
)
loc = locals()
FILENAME_TO_GENFUNC = {
    f"{func_name}.png": loc[func_name]
    for func_name in __all__
    if func_name not in exclude
}

if __name__ == '__main__':
    gen_all_test_plats(FILENAME_TO_GENFUNC, check_new=True, override=False)
