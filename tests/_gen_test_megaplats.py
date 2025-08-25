from pathlib import Path

try:
    from pytrsplat import MegaPlat, Settings
    from ._utils import (
        prepare_settings,
        get_test_settings_for_megaplat,
        add_docstring,
        write_if_new_single,
        gen_all_test_plats,
        RESOURCES_DIR,
        TEST_RESULTS_DIR,
    )

except ImportError:
    import sys

    sys.path.append('../')
    from pytrsplat import MegaPlat, Settings
    from _utils import (
        prepare_settings,
        get_test_settings_for_megaplat,
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
    'megaplat3twprge_nodefaults',
    'megaplat3twprge_defaults40ac',
    'megaplat3twprge_defaults80ac',
    'megaplat3twprge_lotnums_defaults40ac',
    'megaplat3twprge_lotnums_defaults80ac',
    'megaplat3twprge_ns_subset',
    'megaplat3twprge_ew_subset',
    'megaplat3twprge_single_subset',
]

DEFAULT_OUT_DIR = RESOURCES_DIR / 'expected_images' / 'megaplat'
DESC_1 = 'T154N-R97W Sec 1: Lots 1, 2, S/2N/2'
DESC_2 = 'T155N-R97W Sec 6: Lots 2 - 4'
DESC_3 = 'T154N-R96W Sec 8: N/2S/2NW/4'


@add_docstring(
    'MegaPlat - All 3 townships. No default lots.',
    DESC_1, DESC_2, DESC_3
)
def megaplat3twprge_nodefaults(
        fn: str, out_dir: Path = DEFAULT_OUT_DIR, override=False):
    settings = get_test_settings_for_megaplat()
    mega = MegaPlat(settings=settings)
    mega.add_description(DESC_1)
    mega.add_description(DESC_2)
    mega.add_description(DESC_3)
    mega.execute_queue()
    return write_if_new_single(out_dir / fn, mega, override)


@add_docstring(
    'MegaPlat - All 3 townships. 40-acre default lots (not written).',
    DESC_1, DESC_2, DESC_3
)
def megaplat3twprge_defaults40ac(
        fn: str, out_dir: Path = DEFAULT_OUT_DIR, override=False):
    settings = get_test_settings_for_megaplat()
    mega = MegaPlat(settings=settings)
    mega.lot_definer.allow_defaults = True
    mega.lot_definer.standard_lot_size = 40
    mega.add_description(DESC_1)
    mega.add_description(DESC_2)
    mega.add_description(DESC_3)
    mega.execute_queue()
    return write_if_new_single(out_dir / fn, mega, override)


@add_docstring(
    'MegaPlat - All 3 townships. 80-acre default lots (not written).',
    DESC_1, DESC_2, DESC_3
)
def megaplat3twprge_defaults80ac(
        fn: str, out_dir: Path = DEFAULT_OUT_DIR, override=False):
    settings = get_test_settings_for_megaplat()
    mega = MegaPlat(settings=settings)
    mega.lot_definer.allow_defaults = True
    mega.lot_definer.standard_lot_size = 80
    mega.add_description(DESC_1)
    mega.add_description(DESC_2)
    mega.add_description(DESC_3)
    mega.execute_queue()
    return write_if_new_single(out_dir / fn, mega, override)


@add_docstring(
    'MegaPlat - All 3 townships. 40-acre default lots (written).',
    DESC_1, DESC_2, DESC_3
)
def megaplat3twprge_lotnums_defaults40ac(
        fn: str, out_dir: Path = DEFAULT_OUT_DIR, override=False):
    settings = get_test_settings_for_megaplat()
    settings.write_lot_numbers = True
    mega = MegaPlat(settings=settings)
    mega.lot_definer.allow_defaults = True
    mega.lot_definer.standard_lot_size = 40
    mega.add_description(DESC_1)
    mega.add_description(DESC_2)
    mega.add_description(DESC_3)
    mega.execute_queue()
    return write_if_new_single(out_dir / fn, mega, override)


@add_docstring(
    'MegaPlat - All 3 townships. 80-acre default lots (written).',
    DESC_1, DESC_2, DESC_3
)
def megaplat3twprge_lotnums_defaults80ac(
        fn: str, out_dir: Path = DEFAULT_OUT_DIR, override=False):
    settings = get_test_settings_for_megaplat()
    settings.write_lot_numbers = True
    mega = MegaPlat(settings=settings)
    mega.lot_definer.allow_defaults = True
    mega.lot_definer.standard_lot_size = 80
    mega.add_description(DESC_1)
    mega.add_description(DESC_2)
    mega.add_description(DESC_3)
    mega.execute_queue()
    return write_if_new_single(out_dir / fn, mega, override)


@add_docstring(
    'MegaPlat - All 3 townships. 40-acre default lots (unwritten). '
    'Subset output: 154n97w + 155n97w.',
    DESC_1, DESC_2, DESC_3
)
def megaplat3twprge_ns_subset(
        fn: str, out_dir: Path = DEFAULT_OUT_DIR, override=False):
    settings = get_test_settings_for_megaplat()
    mega = MegaPlat(settings=settings)
    mega.lot_definer.allow_defaults = True
    mega.lot_definer.standard_lot_size = 40
    mega.add_description(DESC_1)
    mega.add_description(DESC_2)
    mega.add_description(DESC_3)
    mega.execute_queue(subset_twprges=['154n97w', '155n97w'])
    return write_if_new_single(out_dir / fn, mega, override)



@add_docstring(
    'MegaPlat - All 3 townships. 40-acre default lots (unwritten). '
    'Subset output: 154n96w + 154n97w.',
    DESC_1, DESC_2, DESC_3
)
def megaplat3twprge_ew_subset(
        fn: str, out_dir: Path = DEFAULT_OUT_DIR, override=False):
    settings = get_test_settings_for_megaplat()
    mega = MegaPlat(settings=settings)
    mega.lot_definer.allow_defaults = True
    mega.lot_definer.standard_lot_size = 40
    mega.add_description(DESC_1)
    mega.add_description(DESC_2)
    mega.add_description(DESC_3)
    mega.execute_queue(subset_twprges=['154n96w', '154n97w'])
    return write_if_new_single(out_dir / fn, mega, override)


@add_docstring(
    'MegaPlat - All 3 townships. 40-acre default lots (unwritten). '
    'Subset output: 154n97w.',
    DESC_1, DESC_2, DESC_3
)
def megaplat3twprge_single_subset(
        fn: str, out_dir: Path = DEFAULT_OUT_DIR, override=False):
    settings = get_test_settings_for_megaplat()
    mega = MegaPlat(settings=settings)
    mega.lot_definer.allow_defaults = True
    mega.lot_definer.standard_lot_size = 40
    mega.add_description(DESC_1)
    mega.add_description(DESC_2)
    mega.add_description(DESC_3)
    mega.execute_queue(subset_twprges=['154n97w'])
    return write_if_new_single(out_dir / fn, mega, override)


@add_docstring(
    'MegaPlat - ',
    DESC_1, DESC_2, DESC_3
)
def megaplat3twprge_(
        fn: str, out_dir: Path = DEFAULT_OUT_DIR, override=False):
    settings = get_test_settings_for_megaplat()

    mega = MegaPlat(settings=settings)

    mega.add_description(DESC_1)
    mega.add_description(DESC_2)
    mega.add_description(DESC_3)
    mega.execute_queue()
    return write_if_new_single(out_dir / fn, mega, override)


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
