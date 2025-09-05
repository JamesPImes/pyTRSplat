"""Utils for unit tests."""

import os
import platform
import webbrowser
from typing import Union
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops

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
    'get_expected_subdir',
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
    diff = ImageChops.difference(im1, im2)
    return np.sum(diff) == 0


def image_matches_existing(fp: Path, image: Image.Image):
    """
    Check if the generated ``image`` (either a ``PIL.Image.Image`` or a
    list of them) is the same as the previous one at ``fp``.
    """
    fp = Path(fp)
    if not os.path.exists(fp):
        return False
    existing = Image.open(fp)
    return images_match(existing, image)


def write_if_new_single(fp: Path, plat: Union[Plat, MegaPlat], override=False):
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
            if platform.system() == 'Windows':
                os.startfile(fp_)
            else:
                webbrowser.open_new_tab(str(fp_))
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


def get_expected_subdir():
    """
    Get the subdirectory for this platform: `'win_mac'` for Windows or Mac;
    `'linux'` for Linux.
    """
    # Expected outputs are platform-specific. Must separately generate for
    # Windows (which also works for macOS) and Linux.
    subdir = 'win_mac'
    if platform.system() not in ('Windows', 'Darwin'):
        subdir = 'linux'
    return subdir
