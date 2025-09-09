"""
Generate expected images for ``Plat``.

Must then visually verify they are all correct before running the unit
tests.
"""

import platform
from pathlib import Path

try:
    from pytrsplat import Plat, Settings
    from ._utils import (
        prepare_settings,
        get_test_settings_for_plat,
        images_match,
        image_matches_existing,
        add_docstring,
        write_if_new_single,
        gen_all_test_plats,
        RESOURCES_DIR,
        TEST_RESULTS_DIR,
    )

except ImportError:
    import sys

    sys.path.append('../')
    from pytrsplat import Plat, Settings
    from _utils import (
        prepare_settings,
        get_test_settings_for_plat,
        images_match,
        image_matches_existing,
        add_docstring,
        write_if_new_single,
        gen_all_test_plats,
        RESOURCES_DIR,
        TEST_RESULTS_DIR,
    )

__all__ = [
    'FILENAME_TO_GENFUNC',
    'plat2tracts_nodefaults',
    'plat2tracts_defaults40ac',
    'plat2tracts_defaults80ac',
    'plat2tracts_lotnums_defaults40ac',
    'plat2tracts_lotnums_defaults40ac_only_for_queue',
    'plat2tracts_lotnums_defaults80ac',
    'plat2tracts_writetracts',
    'plat2tracts_writetracts_lotnums',
    'plat3tracts_writetracts_2written',
    'plat1tract_noheader',
    'plat3tracts_separate_layers',
    'plat2tracts_carveout',
]

DEFAULT_OUT_DIR = RESOURCES_DIR / 'expected_images' / 'plat'
if platform.system() == 'Linux':
    DEFAULT_OUT_DIR = DEFAULT_OUT_DIR / 'linux'
else:
    DEFAULT_OUT_DIR = DEFAULT_OUT_DIR / 'win_mac'

DESC_1 = 'T154N-R97W Sec 1: Lots 1, 2, S/2N/2'
DESC_2 = 'T154N-R97W Sec 6: Lots 2 - 4'
DESC_3 = 'T154N-R97W Sec 8: N/2S/2NW/4'


@add_docstring(
    'Plat - Two tracts. No default lots.',
    DESC_1, DESC_2)
def plat2tracts_nodefaults(fn: str, out_dir: Path = DEFAULT_OUT_DIR, override=False):
    settings = get_test_settings_for_plat()
    plat = Plat(settings=settings)
    plat.add_description(DESC_1)
    plat.add_description(DESC_2)
    plat.execute_queue()
    return write_if_new_single(out_dir / fn, plat, override)


@add_docstring(
    'Plat - Two tracts. 40-acre default lots (not written).',
    DESC_1, DESC_2)
def plat2tracts_defaults40ac(fn: str, out_dir: Path = DEFAULT_OUT_DIR, override=False):
    settings = get_test_settings_for_plat()
    plat = Plat(settings=settings)
    plat.lot_definer.allow_defaults = True
    plat.lot_definer.standard_lot_size = 40
    plat.add_description(DESC_1)
    plat.add_description(DESC_2)
    plat.execute_queue()
    return write_if_new_single(out_dir / fn, plat, override)


@add_docstring(
    'Plat - Two tracts. 80-acre default lots (not written).',
    DESC_1, DESC_2)
def plat2tracts_defaults80ac(fn: str, out_dir: Path = DEFAULT_OUT_DIR, override=False):
    settings = get_test_settings_for_plat()
    plat = Plat(settings=settings)
    plat.lot_definer.allow_defaults = True
    plat.lot_definer.standard_lot_size = 80
    plat.add_description(DESC_1)
    plat.add_description(DESC_2)
    plat.execute_queue()
    return write_if_new_single(out_dir / fn, plat, override)


@add_docstring(
    'Plat - Two tracts. 40-acre default lots (written).',
    DESC_1, DESC_2)
def plat2tracts_lotnums_defaults40ac(fn: str, out_dir: Path = DEFAULT_OUT_DIR, override=False):
    settings = get_test_settings_for_plat()
    settings.write_lot_numbers = True
    plat = Plat(settings=settings)
    plat.lot_definer.allow_defaults = True
    plat.lot_definer.standard_lot_size = 40
    plat.add_description(DESC_1)
    plat.add_description(DESC_2)
    plat.execute_queue()
    return write_if_new_single(out_dir / fn, plat, override)


@add_docstring(
    'Plat - Two tracts. 40-acre default lots (written only for queue).',
    DESC_1, DESC_2)
def plat2tracts_lotnums_defaults40ac_only_for_queue(fn: str, out_dir: Path = DEFAULT_OUT_DIR, override=False):
    settings = get_test_settings_for_plat()
    settings.write_lot_numbers = True
    settings.lots_only_for_queue = True
    plat = Plat(settings=settings)
    plat.lot_definer.allow_defaults = True
    plat.lot_definer.standard_lot_size = 40
    plat.add_description(DESC_1)
    plat.add_description(DESC_2)
    plat.execute_queue()
    return write_if_new_single(out_dir / fn, plat, override)

@add_docstring(
    'Plat - Two tracts. 80-acre default lots (written).',
    DESC_1, DESC_2)
def plat2tracts_lotnums_defaults80ac(fn: str, out_dir: Path = DEFAULT_OUT_DIR, override=False):
    settings = get_test_settings_for_plat()
    settings.write_lot_numbers = True
    plat = Plat(settings=settings)
    plat.lot_definer.allow_defaults = True
    plat.lot_definer.standard_lot_size = 80
    plat.add_description(DESC_1)
    plat.add_description(DESC_2)
    plat.execute_queue()
    return write_if_new_single(out_dir / fn, plat, override)


@add_docstring('Plat - Two tracts. Tracts written in footer. No default lots.', DESC_1, DESC_2)
def plat2tracts_writetracts(fn: str, out_dir: Path = DEFAULT_OUT_DIR, override=False):
    settings = get_test_settings_for_plat()
    settings.write_tracts = True
    plat = Plat(settings=settings)
    plat.add_description(DESC_1)
    plat.add_description(DESC_2)
    plat.execute_queue()
    return write_if_new_single(out_dir / fn, plat, override)


@add_docstring(
    'Plat - Two tracts. Tracts written to footer. 40-acre default lots (written).',
    DESC_1, DESC_2)
def plat2tracts_writetracts_lotnums(
        fn: str, out_dir: Path = DEFAULT_OUT_DIR, override=False):
    settings = get_test_settings_for_plat()
    settings.write_tracts = True
    settings.write_lot_numbers = True
    plat = Plat(settings=settings)
    plat.lot_definer.allow_defaults = True
    plat.lot_definer.standard_lot_size = 40
    plat.add_description(DESC_1)
    plat.add_description(DESC_2)
    plat.execute_queue()
    return write_if_new_single(out_dir / fn, plat, override)


@add_docstring(
    'Plat - Three tracts. Tracts written to footer (except 3rd due to margin).',
    DESC_1, DESC_2, DESC_3)
def plat3tracts_writetracts_2written(
        fn: str, out_dir: Path = DEFAULT_OUT_DIR, override=False):
    settings = get_test_settings_for_plat()
    settings.write_tracts = True
    plat = Plat(settings=settings)
    plat.lot_definer.allow_defaults = True
    plat.lot_definer.standard_lot_size = 40
    plat.add_description(DESC_1)
    plat.add_description(DESC_2)
    plat.add_description(DESC_3)
    plat.execute_queue()
    return write_if_new_single(out_dir / fn, plat, override)


@add_docstring('Plat - One tract. No header.', DESC_1)
def plat1tract_noheader(fn: str, out_dir: Path = DEFAULT_OUT_DIR, override=False):
    settings = get_test_settings_for_plat()
    settings.write_header = False
    plat = Plat(settings=settings)
    plat.lot_definer.allow_defaults = True
    plat.lot_definer.standard_lot_size = 40
    plat.add_description(DESC_1)
    plat.execute_queue()
    return write_if_new_single(out_dir / fn, plat, override)


@add_docstring(
    'Plat - Three tracts. Tracts written to different layers (Sec 1 red; Sec 6 green; Sec 8 blue.)',
    DESC_1, DESC_2, DESC_3)
def plat3tracts_separate_layers(
        fn: str, out_dir: Path = DEFAULT_OUT_DIR, override=False):
    settings = get_test_settings_for_plat()
    plat = Plat(settings=settings)
    plat.lot_definer.allow_defaults = True
    plat.lot_definer.standard_lot_size = 40
    plat.add_description(DESC_1, layer='red_layer')
    plat.add_description(DESC_2, layer='green_layer')
    # Default is blue.
    plat.add_description(DESC_3)
    plat.settings.set_layer_fill('red_layer', qq_fill_rgba=(255, 0, 0, 100))
    plat.settings.set_layer_fill('green_layer', qq_fill_rgba=(0, 255, 0, 100))
    plat.execute_queue()
    return write_if_new_single(out_dir / fn, plat, override)


@add_docstring(
    'Plat - Two tracts with different colors. Red Tract 1 (Sec 1) has SE/4NE/4 carve-out.',
    DESC_1, DESC_3)
def plat2tracts_carveout(
        fn: str, out_dir: Path = DEFAULT_OUT_DIR, override=False):
    settings = get_test_settings_for_plat()
    plat = Plat(settings=settings)
    plat.lot_definer.allow_defaults = True
    plat.lot_definer.standard_lot_size = 40
    plat.add_description(DESC_1, layer='red_layer')
    plat.add_description(DESC_3, layer='green_layer')
    carveout_red = 'T154N-R97W Sec 1: SE/4NE/4'
    plat.carve_description(carveout_red, layer='red_layer')
    # Sec 8 carve-out should have no effect, because it's on different layer.
    carveout_noeffect = 'T154N-R97W Sec 8: NW/4'
    plat.carve_description(carveout_noeffect, layer='wrong_layer')
    plat.settings.set_layer_fill('red_layer', qq_fill_rgba=(255, 0, 0, 100))
    plat.settings.set_layer_fill('green_layer', qq_fill_rgba=(0, 255, 0, 100))
    plat.execute_queue()
    return write_if_new_single(out_dir / fn, plat, override)

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
