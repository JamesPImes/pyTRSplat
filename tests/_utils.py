"""Utils for unit tests."""

import os
from pathlib import Path
from hashlib import sha512

from PIL import Image

try:
    from pytrsplat import Settings, Plat, PlatGroup, MegaPlat
except ImportError:
    import sys

    sys.path.append('../')
    from pytrsplat import Settings, Plat, PlatGroup, MegaPlat

__all__ = [
    'images_match',
    'image_matches_existing',
    'write_if_new_single',
    'write_if_new_group',
    'add_docstring',
    'prepare_settings',
    'get_test_settings_for_plat',
    'get_test_settings_for_megaplat',
    'gen_all_test_plats',
    'compare_tests_with_expected',
    'compare_tests_with_expected_group',
    'PRESETS_DIR',
    'RESOURCES_DIR',
    'TEST_RESULTS_DIR',
]

RESOURCES_DIR = Path(__file__).parent / r"_resources"
TEST_RESULTS_DIR = Path(__file__).parent / r"_temp"
PRESETS_DIR = TEST_RESULTS_DIR / 'presets'


def prepare_settings():
    """
    Create a new temp directory for presets, and add the hardcoded
    presets.
    """
    PRESETS_DIR.mkdir(parents=True, exist_ok=True)
    Settings.PRESET_DIRECTORY = PRESETS_DIR
    Settings.restore_presets()
    return None


def get_test_settings_for_plat():
    """
    Get settings for a small ``Plat`` or ``PlatGroup``. Lot numbers and
    tract are off by default, but two rows of text can be written in the
    footer, and lot number font is small enough to be used.

    The results don't look good, but they check the functionality
    correctly.
    """
    test_settings = Settings.preset('square_s')
    # Adjust settings as desired.
    test_settings.set_font('lot', size=8)
    test_settings.lot_num_offset_px = 2
    test_settings.set_font('footer', size=12)
    test_settings.footer_px_below_body = 4
    test_settings.footer_px_between_lines = 4
    test_settings.footer_marg_bottom_y = 0
    return test_settings


def get_test_settings_for_megaplat():
    """
    Get settings for a small ``MegaPlat``. Lot numbers and tract are off
    by default, and lot number font is small enough to be used.

    The results don't look good, but they check the functionality
    correctly.
    """
    test_settings = Settings.preset('megaplat_s')
    # Adjust settings as desired.
    test_settings.set_font('lot', size=8)
    test_settings.lot_num_offset_px = 4
    test_settings.footer_px_below_body = 4
    test_settings.footer_px_between_lines = 4
    test_settings.footer_marg_bottom_y = 0
    return test_settings


def images_match(im1: Image.Image, im2: Image.Image):
    """Check if the two images match."""
    if None in (im1, im2):
        return False
    im1_hash = sha512(im1.tobytes()).hexdigest()
    im2_hash = sha512(im2.tobytes()).hexdigest()
    return im1_hash == im2_hash


def image_matches_existing(fp: Path, image: Image.Image | list[Image.Image]):
    """
    Check if the generated ``image`` (either a ``PIL.Image.Image`` or a
    list of them) is the same as the previous one at ``fp``.
    """
    fp = Path(fp)
    if not os.path.exists(fp):
        return False
    existing = Image.open(fp)
    return images_match(existing, image)


def write_if_new_single(fp: Path, plat: Plat | MegaPlat, override=False):
    """
    Check if the ``Plat`` or ``MegaPlat`` output is different from what
    was previously generated. If any differences, save the output.

    :param override: Mandate writing new file.
    :return: None if no differences. Else, returns the filepath of the
        new file.
    """
    if override or not image_matches_existing(fp, plat.output()):
        plat.output(fp)
        return fp
    return None


def write_if_new_group(fp: Path, platgroup: PlatGroup, override=False):
    """
    Check if any of the ``PlatGroup`` output pages are different from
    what was previously generated. If any differences, save the output.

    :param override: Mandate writing new file.
    :return: None if no differences. Else, returns the list of filepaths
        of the new files.
    """
    surpluses = sorted(platgroup.plats.keys())
    images = platgroup.output()
    fns = [f"{fp.stem} {surp}{fp.suffix}" for surp in surpluses]
    if len(surpluses) == 1:
        fns = [fp.name]
    fps = [fp.parent / fn for fn in fns]
    for fp_, image in zip(fps, images):
        if override or not image_matches_existing(fp_, image):
            platgroup.output(fp)
            return fps
    return None


def add_docstring(explanation: str, *land_descs: str):
    """
    Decorator to add a dynamic docstring to a function for generating a
    plat for unit tests.
    :param explanation: The explanation of which functionality is being
        tested/shown with this function.
    :param land_descs: The descriptions that were added to the queue for
        generating the plat.
    """
    doc = explanation
    for desc in land_descs:
        doc = f"{doc}\n -- {desc}"

    def decorator(func):
        func.__doc__ = doc
        return func

    return decorator


def gen_all_test_plats(filename_to_genfunc: dict, check_new=False, override=False):
    """
    Run all plat generation functions.

    :param filename_to_genfunc: A dict of
        ``{<filename.png>: <function that generates plat at that path>}``
    :param check_new: Show the results of newly created images to user,
        one by one, for approval.
    :param override: (Optional) Ignore existing images, and save all
        outputs, even if they haven't changed.
    """
    prepare_settings()
    new_files = []
    for fn, func in filename_to_genfunc.items():
        fp = func(fn=fn, override=override)
        if fp is None:
            continue
        if isinstance(fp, list):
            fps = fp
        else:
            fps = [fp]
        n = len(fps)
        for i, fp_ in enumerate(fps, start=1):
            new_files.append(fp_)
            if not check_new:
                continue
            os.startfile(fp_)
            response = ''
            while response not in ('y', 'n'):
                print(fp_)
                print(func.__doc__)
                response = input(f"{i} of {n} -- OK? [Y/N] ").lower()
                if response == 'n':
                    os.unlink(fp_)
                    raise RuntimeError('Bad plat. Fix and rerun.')
    if not new_files:
        print('No new images created.')
    return new_files


def compare_tests_with_expected(
        filename_to_genfunc: dict, expected_dir: Path, out_dir: Path
) -> list[str]:
    """
    Generate plats during unit tests, and compare the output against the
    preexisting existing results in ``expected_dir``.

    :param filename_to_genfunc: The ``FILENAME_TO_GENFUNC`` dict from
        ``_gen_test_plats``, ``_gen_test_megaplats``. (Do not use with
        ``_gen_test_platgroups``.)
    :param expected_dir: The path to the directory containing the
        preexisting outputs to compare against.
    :param out_dir: The path to the temp directory in which to save test
        outputs.
    :return: A list of strings, each encoding both the filepath and
        docstring for any outputs that don't match the expected results.
    """
    # Each function in `FILENAME_TO_GENFUNC` is defined in
    # _gen_test_plats, _gen_test_megaplats, or _gen_test_platgroups;
    # and has the signature:
    #       func(fn: <filename>, out_dir: <directory path>, override: bool)
    # And its docstring is an explanation of the settings and input for that plat.
    mismatched = []
    for fn, plat_gen_func in filename_to_genfunc.items():
        expected_fp = expected_dir / fn
        gen_fp = plat_gen_func(fn=fn, out_dir=out_dir, override=True)
        try:
            expected = Image.open(expected_fp)
            generated = Image.open(gen_fp)
        except FileNotFoundError:
            expected = None
            generated = None
        if not images_match(expected, generated):
            failed_plat_explanation = plat_gen_func.__doc__
            mismatched.append(f"{fn}\n{failed_plat_explanation}")
    return mismatched


def compare_tests_with_expected_group(
        filename_to_genfunc: dict, expected_dir: Path, out_dir: Path
) -> list[str]:
    """
    Generate plats during unit tests, and compare the output against the
    preexisting existing results in ``expected_dir``.

    :param filename_to_genfunc: The ``FILENAME_TO_GENFUNC`` dict from
        ``_gen_test_platgroups``. (Do not use with other platting
        classes' test generators.)
    :param expected_dir: The path to the directory containing the
        preexisting outputs to compare against.
    :param out_dir: The path to the temp directory in which to save test
        outputs.
    :return: A list of strings, each encoding both the filepath and
        docstring for any outputs that don't match the expected results.
    """

    # Each function in `FILENAME_TO_GENFUNC` is defined in
    # _gen_test_plats, _gen_test_megaplats, or _gen_test_platgroups;
    # and has the signature:
    #       func(fn: <filename>, out_dir: <directory path>, override: bool)
    # And its docstring is an explanation of the settings and input for that plat.
    def get_base_filename(fn: str):
        """Convert ``'some_plat 154n97w.png'`` to ``'some_plat.png'``."""
        fn_components = fn[:-4].split(' ')
        base = fn_components[0]
        return f"{base}.png"

    existing_files = [
        fn for fn in os.listdir(expected_dir)
        if fn.lower().endswith('.png')
    ]
    base_fns = {}
    for fn in existing_files:
        base_fn = get_base_filename(fn)
        base_fns.setdefault(base_fn, 0)
        base_fns[base_fn] += 1

    mismatched = []
    for top_fn, plat_gen_func in filename_to_genfunc.items():
        gen_fps = plat_gen_func(fn=top_fn, out_dir=out_dir, override=True)
        if base_fns[top_fn] != len(gen_fps):
            failed_plat_explanation = plat_gen_func.__doc__
            mismatched.append(
                f"{top_fn}\n"
                f"({base_fns[top_fn]} images expected, {len(gen_fps)} generated)\n"
                f"{failed_plat_explanation}")
            continue
        for gen_fp in gen_fps:
            # The filename can be different than passed to `plat_gen_func`,
            # because a PlatGroup outputs multiple images when not stacked.
            # So pull the actually-generated filepath.
            gen_fp = Path(gen_fp)
            gen_fn = gen_fp.name
            expected_fp = expected_dir / gen_fn
            try:
                expected = Image.open(expected_fp)
                generated = Image.open(gen_fp)
            except FileNotFoundError:
                expected = None
                generated = None
            if not images_match(expected, generated):
                failed_plat_explanation = plat_gen_func.__doc__
                mismatched.append(f"{gen_fn}\n{failed_plat_explanation}")
    return mismatched
