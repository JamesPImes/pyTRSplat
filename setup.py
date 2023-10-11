import setuptools
from setuptools import setup


MODULE_DIR = "pytrsplat"


def get_constant(constant):
    setters = {
        "version": "__version__ = ",
        "author": "__author__ = ",
        "author_email": "__email__ = ",
        "url": "__website__ = "
    }
    var_setter = setters[constant]
    with open(rf".\{MODULE_DIR}\_constants.py", "r") as file:
        for line in file:
            if line.startswith(var_setter):
                return line[len(var_setter):].strip('\'\n \"')
        raise RuntimeError(f"Could not get {constant} info.")


description = (
    'A library and GUI application for generating customizable plats '
    'from Public Land Survey System (PLSS) land descriptions'
)

long_description = (
    "pyTRSplat (imported as `pytrsplat`) is a Python library and GUI "
    "application for generating "
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
    version=get_constant('version'),
    packages=setuptools.find_packages(),
    url=get_constant('url'),
    license='Modified Academic Public License',
    author=get_constant('author'),
    author_email=get_constant('author_email'),
    description=description,
    long_description=long_description,
    long_description_content_type="text/markdown",
    install_requires=[
        'Pillow<=9.1',
        'piltextbox==0.2.1',
        'pytrs @ git+https://github.com/JamesPImes/pyTRS.git@v2.1.3'
    ],
    python_requires="<3.11",
    include_package_data=True
)
