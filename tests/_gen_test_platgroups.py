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
]

DEFAULT_OUT_DIR = RESOURCES_DIR / 'expected_images' / 'platgroup'
DESC_1 = 'T154N-R97W Sec 1: Lots 1, 2, S/2N/2'
DESC_2 = 'T154N-R97W Sec 6: Lots 2 - 4'
DESC_3 = 'T154N-R96W Sec 8: N/2S/2NW/4'


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
