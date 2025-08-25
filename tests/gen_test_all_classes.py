try:
    from . import _gen_test_plats
    from . import _gen_test_megaplats
    from . import _gen_test_platgroups
    from ._utils import gen_all_test_plats

except ImportError:
    import sys

    sys.path.append('../')
    import _gen_test_plats
    import _gen_test_megaplats
    import _gen_test_platgroups
    from _utils import gen_all_test_plats


def gen_test_outputs(check_new=False, override=False):
    for filename_to_genfunc in (
            _gen_test_plats.FILENAME_TO_GENFUNC,
            _gen_test_megaplats.FILENAME_TO_GENFUNC,
            _gen_test_platgroups.FILENAME_TO_GENFUNC
    ):
        gen_all_test_plats(filename_to_genfunc, check_new, override)


if __name__ == '__main__':
    gen_test_outputs(check_new=True)
