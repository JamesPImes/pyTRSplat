from setuptools import setup

from pyTRSplat import _constants

description = (
    'A library and GUI application for generating customizable plats '
    'from Public Land Survey System (PLSS) land descriptions'
)

long_description = (
    "pyTRSplat is a Python library and GUI application for generating "
    "customizable plats directly from Public Land Survey System (PLSS) "
    "land descriptions (or 'legal descriptions'), built on the "
    "[pyTRS library](https://github.com/JamesPImes/pyTRS)."
    "\n\n"
    "Can be imported as a module, or the GUI application provides "
    "essentially all of the functionality as well."
    "\n\n"
    "Visit [the GitHub repository](https://github.com/JamesPImes/pyTRSplat) "
    "for a quickstart guide."
)


setup(
    name='pyTRSplat',
    version=_constants.__version__,
    packages=[
        'pyTRSplat', 'pyTRSplat.grid', 'pyTRSplat.plat', 'pyTRSplat.utils',
        'pyTRSplat.platqueue', 'pyTRSplat.imgdisplay', 'pyTRSplat.platsettings',
        'pyTRSplat.settingseditor'
    ],
    url=_constants.__website__,
    license='Modified Academic Public License',
    author=_constants.__author__,
    author_email=_constants.__email__,
    description=description,
    long_description=long_description,
    long_description_content_type="text/markdown",
    include_package_data=True
)
