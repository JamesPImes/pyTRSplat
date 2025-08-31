import pytest

try:
    from .test_plat import *
    from .test_megaplat import *
    from .test_platgroup import *
    from .test_lot_definer import *
    from .test_settings import *
except ImportError:
    from test_plat import *
    from test_megaplat import *
    from test_platgroup import *
    from test_lot_definer import *
    from test_settings import *

if __name__ == '__main__':
    prepare_settings()
    pytest.main()
