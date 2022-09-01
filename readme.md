# pyTRSplat

A python module (imported as `pytrsplat`) and application for generating customizable plat images of PLSS descriptions (or 'legal descriptions') of land; building on the [pyTRS library](https://github.com/JamesPImes/pyTRS), which parses the raw land descriptions into their component parts.

## To install

Directly from the GitHub repo:
```
pip install git+https://github.com/JamesPImes/pyTRSplat@master
```


## Sample Outputs

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

...or the following letter-sized plat, with tracts written at the end (using a different setting):

![sample_plat_01](documentation/sample_plat_01.png)

...or could be configured any number of ways for different sizes, fonts, colors, page size/shape, etc.


## Included GUI Application

A full-featured GUI application is included as `pyTRSplat_app_windowed.pyw`. The interface is a little rough-around-the-edges (especially the custom settings editor), but it has nearly all of the features of the module.

Lands can be added either by entering their PLSS description as raw text, or by manually selecting which QQ's to fill -- or both methods. It currently will save to PNG or PDF.

![plat_gui_01](documentation/plat_gui_01.gif)

## Quick demonstration of pyTRSplat as a module

The sample code block below is a demonstration of the basic functionality of converting text into a plat. See the next section of this readme for more fine-grained explanations.

```
import pytrsplat

land_description = '''Township 154 North, Range 97 West
Section 1: Lots 1 - 3, S/2N/2
Section 5: Lot 4, The South Half of the Northwest Quarter, and The Southwest Quarter
Section 6: Lots 1 - 7, S/2NE/4, SE/4NW/4, E/2SW/4, SE/4
Section 13: That portion of the E/2 lying north of the river and west of the private road right-of-way as more particularly described in Book 1234 / Page 567, recorded on January 1, 1964 in the records of Example County, as amended in that Right-of-Way Amendment Agreement dated December 10, 1987, recorded on December 11, 1987 as Document No. 1987-1234567 of the records of Example County.
Section 14: NE/4'''

# Using the 'letter' settings preset (i.e. letter-sized paper at 200ppi),
# generate the plat, and save as .png to the specified filepath.
plats = pytrsplat.text_to_plats(
    land_description,
    settings='letter',
    output_filepath=r'C:\land plats\sample_plat_01.png')
```

## "How-To"

For additional functionality, including customization of the plats, and defining where lots lie within a given section, see [the more in-depth guide](documentation/guide.md).


## Requirements

* Python 3.6+
* Windows 10+