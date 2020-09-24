# pyTRSplat

A python module and application for generating customizable plat images of PLSS descriptions (or 'legal descriptions') of land. Uses the [pyTRS library](https://github.com/mesji/pyTRS) for parsing raw land descriptions into their component parts and the [Pillow (PIL) library](https://python-pillow.org/) for drawing the plats.


### Sample Outputs

Processing the following example PLSS land description...
```
Township 154 North, Range 97 West
Section 1: Lots 1 - 3, S/2N/2
Section 5: Lot 4, The South Half of the Northwest Quarter, and The Southwest Quarter
Section 6: Lots 1 - 7, S/2NE/4, SE/4NW/4, E/2SW/4, SE/4
Section 13: That portion of the E/2 lying north of the river and west of the private road right-of-way as more particularly described in Book 1234 / Page 567, recorded on January 1, 1964 in the records of Example County, as amended in that Right-of-Way Amendment Agreement dated December 10, 1987, recorded on December 11, 1987 as Document No. 1987-1234567 of the records of Example County.
Section 14: NE/4
```
...results in the following square plat (using one custom setting):

![sample_plat_01](documentation/sample_plat_02.png)

...or the following letter-sized plat (using a different setting):

![sample_plat_01](documentation/sample_plat_01.png)

...or could be configured any number of ways for different sizes, fonts, colors, page size/shape, etc.


### Included GUI Application

A full-featured GUI application is included as `pyTRSplat_window.pyw`. The interface is a little rough-around-the-edges (especially the custom settings editor), but it has nearly all of the features of the module.

Lands can be added either by entering their PLSS description as raw text, or by manually selecting which QQ's to fill -- or both methods. It currently will save to PNG or PDF.

![gui_01](documentation/gui_01.png)

### Quick demonstration of pyTRSplat as a module

Below is a demonstration of very basic functionality of converting text into a plat.

(However, plats can be worked with more in-depth. Look into `Plat` and `MultiPlat` objects in `pyTRSplat.Plat`. And configure settings with a `Settings` object in `pyTRSplat.PlatSettings`. If platting multiple sources onto a single plat, look into `PlatQueue` and `MultiPlatQueue` objects in `pyTRSplat.PlatQueue`.)

```
import pyTRSplat

# The PLSS description of the land we want to plat.
land_description = 'T154N-R97W Sec 14: NE/4, Sec 15: W/2, Sec 22: Lot 1, S/2NE/4'

# This .csv file is included in the assets\examples\ directory. It defines what 
# lot 1 means in Section 22, T154N-R97W (and other lots/sections).
lot_database_fp = r'assets\examples\SAMPLE_LDDB.csv'

# Output to a .png file (could also output to .pdf)
output_fp = r'C:\land plats\sample_plat_01.png'

# Using the 'letter' settings preset (i.e. letter-sized paper at 200ppi),
# generate the plat
plats = pyTRSplat.text_to_plats(
    land_description, settings='letter', lddb=lot_database_fp, 
    output_filepath=output_fp)

# Specifying `output_filepath=` saved the plat to the specified fp. The function
# also returns a list of the Image objects of the plats (in this case only one 
# Image in the list), and we've set the list to variable `plats`, in case we
# want to use them for something else.

# Optionally customize the plat output by creating a Settings object
set_obj = pyTRSplat.Settings(preset='letter')
set_obj.write_header = False  # Disable writing of header
set_obj.qq_side = 12  # 12px per side of each QQ square

# ... Or use the GUI Settings customizer in `SettingsEditor.py` to create,
# edit, and save presets

plats_2 = pyTRSplat.text_to_plats(
    land_description, settings=set_obj, lddb=lot_database_fp, 
    output_filepath=output_fp)
```

