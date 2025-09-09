import platform
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
    'platgroup2tracts2twprges_lotnums_defaults40ac_only_for_queue',
    'platgroup2tracts_defaults40ac',
    'platgroup2tracts_defaults80ac',
    'platgroup2tracts_lotnums_defaults40ac',
    'platgroup2tracts_lotnums_defaults80ac',
    'platgroup2tracts_writetracts',
    'platgroup2tracts_writetracts_lotnums',
    'plat3tracts_writetracts_2written',
    'platgroup3tracts_separate_layers',
    'platgroup2tracts_carveout',
]

DEFAULT_OUT_DIR = RESOURCES_DIR / 'expected_images' / 'platgroup'
if platform.system() == 'Linux':
    DEFAULT_OUT_DIR = DEFAULT_OUT_DIR / 'linux'
else:
    DEFAULT_OUT_DIR = DEFAULT_OUT_DIR / 'win_mac'

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
    'PlatGroup - Two tracts, two Twp/Rge. 40-acre default lots (written).',
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
    'PlatGroup - Two tracts, one Twp/Rge. 40-acre default lots (written only for queue).',
    DESC_1, DESC_3)
def platgroup2tracts2twprges_lotnums_defaults40ac_only_for_queue(fn: str, out_dir: Path = DEFAULT_OUT_DIR, override=False):
    settings = get_test_settings_for_plat()
    settings.write_lot_numbers = True
    settings.lots_only_for_queue = True
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


@add_docstring(
    'PlatGroup - Three tracts. Tracts written to different layers (Sec 1 red; Sec 6 green; Sec 12 blue.)',
    DESC_1, DESC_2, DESC_4)
def platgroup3tracts_separate_layers(
        fn: str, out_dir: Path = DEFAULT_OUT_DIR, override=False):
    settings = get_test_settings_for_plat()
    pg = PlatGroup(settings=settings)
    pg.lot_definer.allow_defaults = True
    pg.lot_definer.standard_lot_size = 40
    pg.add_description(DESC_1, layer='red_layer')
    pg.add_description(DESC_2, layer='green_layer')
    # Default is blue.
    pg.add_description(DESC_4)
    pg.settings.set_layer_fill('red_layer', qq_fill_rgba=(255, 0, 0, 100))
    pg.settings.set_layer_fill('green_layer', qq_fill_rgba=(0, 255, 0, 100))
    pg.execute_queue()
    return write_if_new_group(out_dir / fn, pg, override)

@add_docstring(
    'PlatGroup - Two tracts with different colors. Red Tract 1 (Sec 1) has SE/4NE/4 carve-out.',
    DESC_1, DESC_3)
def platgroup2tracts_carveout(
        fn: str, out_dir: Path = DEFAULT_OUT_DIR, override=False):
    settings = get_test_settings_for_plat()
    pg = PlatGroup(settings=settings)
    pg.lot_definer.allow_defaults = True
    pg.lot_definer.standard_lot_size = 40
    pg.add_description(DESC_1, layer='red_layer')
    pg.add_description(DESC_3, layer='green_layer')
    carveout_red = 'T154N-R97W Sec 1: SE/4NE/4'
    pg.carve_description(carveout_red, layer='red_layer')
    # Sec 8 carve-out should have no effect, because it's on different layer.
    carveout_noeffect = 'T154N-R96W Sec 8: NW/4'
    pg.carve_description(carveout_noeffect, layer='wrong_layer')
    pg.settings.set_layer_fill('red_layer', qq_fill_rgba=(255, 0, 0, 100))
    pg.settings.set_layer_fill('green_layer', qq_fill_rgba=(0, 255, 0, 100))
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
