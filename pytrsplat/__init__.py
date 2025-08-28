# Copyright (c) 2020-2025, James P. Imes. All rights reserved.

"""
pyTRSplat (imported as ``pytrsplat``) is a library for generating
customizable land plat images from PLSS land descriptions (or
'legal descriptions'), using the pyTRS parsing library.
"""

from . import _constants
from .plat_gen import *

__version__ = _constants.__version__
__version_date__ = _constants.__version_date__
__author__ = _constants.__author__
__email__ = _constants.__email__
__license__ = _constants.__license__


def version():
    """Return the current version and version date as a string."""
    return f'v{__version__} - {__version_date__}'
