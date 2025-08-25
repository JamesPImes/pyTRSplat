import unittest
from pathlib import Path

try:
    from pytrsplat import PlatGroup, Settings
    from ._utils import (
        prepare_settings,
        get_test_settings_for_plat,
        compare_tests_with_expected_group,
        RESOURCES_DIR,
        TEST_RESULTS_DIR,
    )
    from ._gen_test_platgroups import (
        FILENAME_TO_GENFUNC,
    )
except ImportError:
    import sys

    sys.path.append('../')
    from pytrsplat import PlatGroup, Settings
    from ._utils import (
        prepare_settings,
        get_test_settings_for_plat,
        compare_tests_with_expected_group,
        RESOURCES_DIR,
        TEST_RESULTS_DIR,
    )
    from ._gen_test_platgroups import (
        FILENAME_TO_GENFUNC,
    )


class TestPlatGroupBehavior(unittest.TestCase):
    def test_init(self):
        plat_group = PlatGroup()
        self.assertTrue(len(plat_group.queue) == 0)


class TestPlatGroupOutput(unittest.TestCase):
    """Test the output results for PlatGroup."""

    expected_dir: Path = RESOURCES_DIR / 'expected_images' / 'platgroup'
    out_dir: Path = TEST_RESULTS_DIR / 'platgroup'

    @classmethod
    def setUpClass(cls):
        prepare_settings()

    def test_matching_outputs(self):
        """
        Generate test platgroups and compare their output to expected
        results.

        (See ``_gen_test_platgroups.py`` for the inputs/settings for the
        various platgroups.)
        """
        mismatched = compare_tests_with_expected_group(
            FILENAME_TO_GENFUNC,
            expected_dir=self.expected_dir,
            out_dir=self.out_dir,
        )
        msg = {f"Mismatched output(s):\n{'\n\n'.join(mismatched)}"}
        self.assertTrue(len(mismatched) == 0, msg)
        return None


if __name__ == '__main__':
    unittest.main()
