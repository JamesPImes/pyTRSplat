import unittest
from pathlib import Path

try:
    from pytrsplat import MegaPlat, Settings
    from ._utils import (
        prepare_settings,
        get_test_settings_for_megaplat,
        compare_tests_with_expected,
        RESOURCES_DIR,
        TEST_RESULTS_DIR,
    )
    from ._gen_test_megaplats import (
        FILENAME_TO_GENFUNC,
    )
except ImportError:
    import sys

    sys.path.append('../')
    from pytrsplat import MegaPlat, Settings
    from _utils import (
        prepare_settings,
        get_test_settings_for_megaplat,
        compare_tests_with_expected,
        RESOURCES_DIR,
        TEST_RESULTS_DIR,
    )
    from _gen_test_megaplats import (
        FILENAME_TO_GENFUNC,
    )


class TestMegaPlatBehavior(unittest.TestCase):
    def test_init(self):
        megaplat = MegaPlat()
        self.assertTrue(len(megaplat.queue) == 0)


class TestMegaPlatOutput(unittest.TestCase):
    """Test the output results for MegaPlat."""

    expected_dir: Path = RESOURCES_DIR / 'expected_images' / 'megaplat'
    out_dir: Path = TEST_RESULTS_DIR / 'megaplat'

    @classmethod
    def setUpClass(cls):
        prepare_settings()

    def test_matching_outputs(self):
        """
        Generate test megaplats and compare their output to expected
        results.

        (See ``_gen_test_megaplats.py`` for the inputs/settings for the
        various megaplats.)
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
