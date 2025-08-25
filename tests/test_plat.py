import unittest
from pathlib import Path

try:
    from pytrsplat import Plat, Settings
    from ._utils import (
        prepare_settings,
        get_test_settings_for_plat,
        compare_tests_with_expected,
        RESOURCES_DIR,
        TEST_RESULTS_DIR,
    )
    from ._gen_test_plats import (
        FILENAME_TO_GENFUNC,
    )
except ImportError:
    import sys

    sys.path.append('../')
    from pytrsplat import Plat, Settings
    from _utils import (
        prepare_settings,
        get_test_settings_for_plat,
        compare_tests_with_expected,
        RESOURCES_DIR,
        TEST_RESULTS_DIR,
    )
    from _gen_test_plats import (
        FILENAME_TO_GENFUNC,
    )


class TestPlatBehavior(unittest.TestCase):
    expected_dir: Path = RESOURCES_DIR / 'expected_images' / 'plat'
    out_dir: Path = TEST_RESULTS_DIR / 'plat'

    def test_init(self):
        plat = Plat('154n', '97w')
        self.assertEqual(plat.twp, '154n')
        self.assertEqual(plat.rge, '97w')


class TestPlatOutput(unittest.TestCase):
    """Test the output results for Plat."""

    expected_dir: Path = RESOURCES_DIR / 'expected_images' / 'plat'
    out_dir: Path = TEST_RESULTS_DIR / 'plat'

    @classmethod
    def setUpClass(cls):
        prepare_settings()

    def test_matching_outputs(self):
        """
        Generate test plats and compare their output to expected results.

        (See ``_gen_test_plats.py`` for the inputs/settings for the
        various plats.)
        """
        mismatched = compare_tests_with_expected(
            FILENAME_TO_GENFUNC,
            expected_dir=self.expected_dir,
            out_dir=self.out_dir,
        )
        msg = {f"Mismatched output(s):\n{'\n\n'.join(mismatched)}"}
        self.assertTrue(len(mismatched) == 0, msg)
        return None


if __name__ == '__main__':
    unittest.main()
