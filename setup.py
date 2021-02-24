from setuptools import setup


def get_version():
    version_var_setter = "__version__ = "
    with open(r".\pyTRSplat\_constants.py", "r") as file:
        for line in file:
            if line.startswith(version_var_setter):
                version = line[len(version_var_setter):].strip('\'\n \"')
                return version
        raise RuntimeError("Could not get __version__ info.")


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
    version=get_version(),
    packages=[
        'pyTRSplat',
        'pyTRSplat.grid',
        'pyTRSplat.plat',
        'pyTRSplat.utils',
        'pyTRSplat.platqueue',
        'pyTRSplat.imgdisplay',
        'pyTRSplat.platsettings',
        'pyTRSplat.settingseditor'
    ],
    url='https://github.com/JamesPImes/pyTRSplat',
    license='Modified Academic Public License',
    author='James P. Imes',
    author_email='jamesimes@gmail.com',
    description=description,
    long_description=long_description,
    long_description_content_type="text/markdown",
    include_package_data=True
)
