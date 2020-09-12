# pyTRSplat

A python module for generating configurable plat images of PLSS descriptions (or 'legal descriptions') of land. Uses the [pyTRS library](https://github.com/mesji/pyTRS) for parsing raw land descriptions into their component parts and the [Pillow (PIL) library](https://python-pillow.org/) for drawing the plats.


### Quick demonstration

Below is a demonstration of very basic functionality of converting text into a plat.

(However, plats can be worked with more in-depth. Look into `Plat` and `MultiPlat` objects in `pyTRSplat.plat`. And configure settings with a `Settings` object in `pyTRSplat.platsettings`. If platting multiple sources onto a single plat, look into `PlatQueue` and `MultiPlatQueue` objects in `pyTRSplat.platqueue`.)

```
import pyTRSplat

# The PLSS description of the land we want to plat.
land_description = 'T154N-R97W Sec 14: NE/4, Sec 15: W/2, Sec 22: Lot 1, S/2NE/4'

# This .csv file is included in the assets\examples\ directory. It defines what 
# lot 1 means in Section 22, T154N-R97W (and other lots/sections).
lot_database_fp = r'assets\examples\SAMPLE_LDDB.csv'

# Output to a .png file (could also output to .pdf)
output_fp = r'C:\land plats\sample_plat_01.png'

# Using the 'letter' settings preset (i.e. letter-sized paper at 200ppi)
plats = pyTRSplat.text_to_plats(
    land_description, settings='letter', lddb=lot_database_fp, 
    output_filepath=output_fp)

# Specifying `output_filepath=` saved the plat to the specified fp. It also
# returned a list of the Image objects of the plats (in this case only one 
# Image in the list), and we set the list to variable `plats`, in case we want
# to use them for something else.
```

...resulting in the following plat:
![sample_plat_01](documentation/sample_plat_01.png)