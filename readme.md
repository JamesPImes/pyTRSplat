# pyTRSplat

A python module and application for generating customizable plat images of PLSS descriptions (or 'legal descriptions') of land. Uses the [pyTRS library](https://github.com/JamesPImes/pyTRS) for parsing raw land descriptions into their component parts and the [Pillow (PIL) library](https://python-pillow.org/) for drawing the plats. (And also a small role for the [piltextbox module](https://github.com/JamesPImes/piltextbox), which was spun off from this project.)


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

A full-featured GUI application is included as `pyTRSplat_window.pyw`. The interface is a little rough-around-the-edges (especially the custom settings editor), but it has nearly all of the features of the module.

Lands can be added either by entering their PLSS description as raw text, or by manually selecting which QQ's to fill -- or both methods. It currently will save to PNG or PDF.

![gui_01](documentation/gui_01.png)

## Quick demonstration of pyTRSplat as a module

The sample code block below is a demonstration of very basic functionality of converting text into a plat.

However, plats can be worked with more in-depth.

## Bird's-eye view of module classes and functions

### Quickly generate plats from raw land descriptions with `text_to_plats()`
This convenience function is the simplest way to generate plats, other than the GUI application. It takes as input a raw PLSS land description (optionally using `pyTRS` config parameters for configuring how it should be parsed), and returns flattened PIL.Image objects of the generated plats, optionally saving them to filepath as .png or .pdf files.
Example:
```
import pyTRSplat

land_description = 'T154N-R97W, Sec 14: NE/4, Sec 15: W/2'

# Using the 'letter' preset (i.e. 8.5"x11" paper at 200ppi, etc.), generate plat
# and save to the specified filepath; returns a list containing a single plat (because
# there was only one Twp/Rge in the land description)
plats = pyTRSplats.text_to_plats(
    land_description, settings='letter', output_filepath=r'C:\Land\Plats\example_plat.png')

# print to console the type of the first element in the list `plats`:
print(type(plats[0]))  # prints '<class 'PIL.Image.Image'>'
```



### Get more control with `Plat` and `MultiPlat` objects
For generating more nuanced or complicated plats, or incorporating data from multiple sources, these are the objects to use.
`pyTRSplat.Plat` -- A single plat, comprising a single PLSS township of land. (Can also plat a single section. See `pyTRSplat.Plat` documentation on `only_section=<int>` parameter.)

`pyTRSplat.MultiPlat` -- A collection of any number of plats (i.e. `pyTRSplat.Plat` objects, stored as a list in the `.plats` attribute), all sharing identical settings and general parameters, and each comprising a single PLSS township of land. These can also handle `pyTRS.PLSSDesc` objects, whereas `Plat` objects cannot (because `PLSSDesc` objects can span multiple Twp/Rge).



#### `Plat` example
```
import pyTRSplat

# Create a Plat with the 'legal' preset (i.e. 8.5x14" paper at 200ppi, etc.);
# will show a grid of all 36 sections, with the header 'Township 154 North, Range 97 West'
# but with no specific lands projected onto it yet.
plat_1 = pyTRSplat.Plat(twp='154n', rge='97w', settings='legal')

# We'll import pyTRS, a module for parsing land descriptions (which this module builds on)
import pyTRS

# Creating a tract, being the NE/4 of Section 14, T154N-R97W
tract_1 = pyTRS.Tract(trs='154n97w14', desc='NE/4')

# Parsing it into lots/QQs; not bothering with any optional `config=` parameters here.
tract_1.parse()

# Project the parsed `tract_1` onto our plat, which will now show the NE/4 of Section 14
# colored in, and '154n97w14: NE/4' written below the grid.
plat_1.plat_tract(tract_1)

# Flatten and save the plat to this filepath:
plat_1.output(r'C:/Land/Plats/sample_01.png')
```



#### `MultiPlat` example
```
import pyTRSplat

# Create a MultiPlat with the 'legal' preset (i.e. 8.5x14" paper at 200ppi, etc.).
# No Plats will be created at init, but any that do get created later will use the same
# 'legal' preset.
multiplat_1 = pyTRSplat.MultiPlat(settings='legal')

# We'll import pyTRS, a module for parsing land descriptions (which this module builds on)
import pyTRS

# Creating a PLSSDesc object, spanning lands in T154N-R97W and T155N-R97W
sample_text = 'T154N-R97W Sec 14: SE/4, Sec 15: W/2, T155N-R97W Sec 22: S/2'
plssdesc_1 = pyTRS.PLSSDesc(sample_text)

# Parse `plssdesc_1` it into pyTRS.Tract objects, which get parsed into lots/QQs by virtue
# of the parameter initParseQQ=True (see pyTRS docs for more info); also not bothering with
# any optional `config=` parameters here.
plssdesc_1.parse(initParseQQ=True)

# `plssdesc_1` now has 3 Tracts in `.parsedTracts` attribute, being in 154n97w14, 154n97w15,
# and 155n97w22 (i.e. there are two unique Twp/Rges: 154n97w and 154n98w).

# Process the parsed `plssdesc_1` onto our MultiPlat, which will now create two Plat objects,
# one for T154N-R97W and another for T155N-R97W, each with the appropriate lands colored in,
# and the corresponding tracts written at the bottom (which can be enabled or disabled in
# a Settings object)
multiplat_1.plat_plssdesc(plssdesc_1)

# Can access either of the generated Plat objects, which are stored in `.plats` attribute:
plat_154n97w = multiplat_1.plats[0]
plat_155n97w = multiplat_1.plats[1]

# Flatten and save both of the generated Plats to a PDF the this filepath:
multiplat_1.output_to_pdf(r'C:/Land/Plats/sample_01.pdf')
```



### Easily handle multiple data sources with `PlatQueue` and `MultiPlatQueue` objects

These objects can streamline generating `Plat` and `MultiPlat` objects with data from multiple sources:

* `pyTRSplat.PlatQueue` -- A list (with additional functionality) of objects that can be projected onto a single `Plat` with the `Plat.process_queue()` or `Plat.from_queue()` methods.

* `pyTRSplat.MultiPlatQueue` -- A dict, keyed by Twp/Rge (e.g., `'154n97w'` or `'1s7e'`) of `PlatQueue` objects applicable to the respective Twp/Rge. This object can be sorted and automatically processed into the appropriate `Plat` object in a `MultiPlat` with the `MultiPlat.process_queue()` or `MultiPlat.from_queue()` methods.

#### (some example data sources)
```
# First, create some example pyTRS.Tract and pyTRS.PLSSDesc objects

import pyTRS

# Creating a couple tracts, and parsing them into lots/QQs with the pyTRS module
tract_1 = pyTRS.Tract(trs='154n97w14', desc='NE/4')
tract_1.parse()
tract_2 = pyTRS.Tract(trs='154n97w13', desc='W/2NW/4')
tract_2.parse()

# Creating a couple PLSSDesc objects, spanning lands in T154N-R97W, T155N-R97W, T156N-R97W
sample_text_1 = 'T154N-R97W Sec 14: SE/4, Sec 15: W/2, T155N-R97W Sec 22: S/2'
plssdesc_1 = pyTRS.PLSSDesc(sample_text_1)
sample_text_2 = 'T154N-R97W Sec 11: S/2SE/4, T156N-R97W Sec 36: S/2S/2'
plssdesc_2 = pyTRS.PLSSDesc(sample_text_2)

# parsing them into pyTRS.Tract objects, which get parsed into lots/QQs by virtue of the
# parameter initParseQQ=True (see pyTRS docs for more info)
plssdesc_1.parse(initParseQQ=True)
plssdesc_2.parse(initParseQQ=True)

```
#### `PlatQueue` example
```
# (using the example pyTRS objects from the above block of sample code)

import pyTRSplat

pq1 = pyTRSplat.PlatQueue()

# Both `tract_1` and `tract_2` can be added to the same PlatQueue object, because
# they represent lands in the same Twp/Rge. (It would not raise an error if they
# were different Twp/Rge, because PlatQueue objects are agnostic to Twp/Rge, but the
# resulting plats would be inaccurate.)
pq1.queue_add(tract_1)
pq1.queue_add(tract_2)

# Create a Plat and process the contents of `pq1`:

plat_1 = pyTRSplat.Plat(settings='letter')
plat_1.process_queue(pq1)

# plat_1 has now colored in the lands in `tract_1` and `tract_2`, and written their text
# below the grid (because that feature is enabled in the 'letter' preset)

# NOTE: PLSSDesc objects cannot be added to a PlatQueue, and it would raise an error if we
# tried. This is because a PLSS description can span multiple Twp/Rge's, whereas a single
# Plat can only depict one Twp/Rge.

```
#### `MultiPlatQueue` example
```
# (using the example pyTRS objects from the above block of sample code)

# Unlike with PlatQueue objects, pyTRS.PLSSDesc objects can be added to a MultiPlatQueue object,
# which does allow multiple Twp/Rge's.
# (a MultiPlatQueue object is NOT agnostic to Twp/Rge, and in fact Twp/Rge serves as its dict
# keys -- ex: '154n97w' or '1s7e' etc.)

mpq1 = pyTRSplat.MultiPlatQueue()

# Add to `mpq1` our two PLSSDesc objects, and the subordinate pyTRS.Tract objects are
# automatically sorted by Twp/Rge and added to the appropriate PlatQueue within `mpq1`
mpq1.queue_add(plssdesc_1)
mpq1.queue_add(plssdesc_2)

mpq1['154n97w']  # returns a PlatQueue object containing the pyTRS.Tract objects in T154N-R97W
mpq1['155n97w']  # Does the same, for T155N-R97W
mpq1['156n97w']  # Does the same, for T156N-R97W
#mpq1['157n97w']  # This would raise a KeyError, because there were no tracts in T157N-R97W

# We can also add the two pyTRS.Tract objects to the MultiPlatQueue, if we want. Specifying
# the `twprge` (i.e. the appropriate dict key for these objects) here is optional, because
# the MultiPlatQueue can deduce it from the Tract objects' own `.twp` and `.rge` attributes.
# However, specifying `twprge` is good practice, because the pyTRS parsing algorithm is not
# infallible and could have misread the Twp/Rge (or maybe `twp` / `rge` were not specified when
# the Tract objects were initialized).
mpq1.queue_add(tract_1, twprge='154n97w')
mpq1.queue_add(tract_2, twprge='154n97w')


multiplat_1 = pyTRSplat.MultiPlat(settings='letter')
multiplat_1.process_queue(mpq1)

# `multiplat_1` has now generated three plats (for T154N-R97W, T155N-R97W, and T156N-R97W), with
# the lands colored in and tract text written, each using the 'letter' preset.

```

Note that specifying `twprge` when adding a `pyTRS.PLSSDesc` via `MultiPlatQueue.queue_add()` has no effect. Because PLSS descriptions can have multiple Twp/Rge's, `MultiPlatQueue` objects mandate pulling the the Twp/Rge(s) from the `.twp` and `.rge` attributes of the `pyTRS.Tract` objects listed in the `.parsedTracts` attribute of the `PLSSDesc` object.

Note also that `pyTRSplat.SectionGrid` and `pyTRSplat.TownshipGrid` objects can also be added to `PlatQueue` and `MultiPlatQueue` objects (for MPQ's, requiring `twprge` to be specified when added), but those objects



#### `MultiPlatQueue.queue_add_text()` method example
```
# This...

import pyTRS
import pyTRSplat

sample_text_3 = 'T154N-R97W Sec 1: Lots 1 - 3, S/2N/2'
plssdesc_3 = pyTRS.PLSSDesc(sample_text, config='cleanQQ')
plssdesc_3.parse()
mpq2 = pyTRSplat.MultiPlatQueue()
mpq2.queue_add(plssdesc_3)


# ... is functionally equivalent to this:

import pyTRSplat

mpq2 = pyTRSplat.MultiPlatQueue()
sample_text_3 = 'T154N-R97W Sec 1: Lots 1 - 3, S/2N/2'
mpq2.queue_add_text(sample_text_3, config='cleanQQ')


# i.e. `.queue_add_text()` takes raw text of a PLSS land description, parses it (taking the
# same optional pyTRS `config=` parameters), and adds the results to the MultiPlatQueue

```


### Configure the output with `Settings` objects, including presets and custom settings

`pyTRSplat.Settings` -- Configure the look and behavior of Plat and MultiPlat objects (e.g., size, colors, fonts, whether to write headers/tracts/etc.). Default and presets are available and customizable.

Wherever a `settings=` parameter appears within this module, it can take either the name of a preset (a string, ex: `'letter'`, `'legal (gray)'`, `'square_m'`, etc.) or as a `pyTRSplat.Settings` object.



```
import pyTRSplat

# Using the 'square_m' preset...
plat_1 = pyTRSplat.Plat(twp='154n', rge='97w', setting='square_m')


# Or generate a custom settings object, starting from the 'letter' preset...
custom_setting_1 = pyTRSplat.Settings('letter')
# ...disable writing the header:
custom_setting_1.write_header = False
# ...and change the font for writing section numbers, to 'Mono' (a Courier-like font):
custom_setting_1.set_font('sec', Settings.TYPEFACES['Mono'])

# Now create a Plat using this custom setting:
plat_2 = Plat(twp='154n', rge='97w', setting=custom_setting_1)
```



*__Note:__ To see a current list of available `Settings` presets, call `pyTRSplat.Settings.list_presets()`*

*__Note:__ For a GUI application for viewing / editing / saving `Settings` presets, call `pyTRSplat.launch_settings_editor()`*

*[__#TODO:__ List out all `Settings` attributes, and what they control. They can all be set with the `.launch_settings_editor()`, of course, but should provide a guide to setting them programatically.]*



### Getting into the weeds with lot definitions -- `LotDefinitions`, `TwpLotDefinitions`, and `LotDefDB` objects
The most efficient way to define lots is to do so externally in a .csv file, and load them into a `pyTRSplat.LotDefDB` with init parameter `from_csv=<filepath>`. (See below.) __[#TODO: Link to that part of the readme]__



#### Why do we need lot definitions, anyway?

Quarter-quarters (QQs) are not ambiguous (i.e. the NE/4NE/4 or `'NENE'` is always in the same place in any section\*\*). However, by design of the PLSS, lots can occur anywhere within a section (which is the point of using lots instead of QQs in the first place -- to handle variations in the land). Thus, we need some method for interpreting the lots in terms of QQs (e.g., in a 'typical' Section 1, Lot 1 is equivalent to the NE/4NE/4).



\*\* *Caveat: Non-standard sections with out-of-place QQs do exist but are relatively rare in most parts of the United States. In any case, such sections cannot be handled reliably by the current version of this module.*

In this module, lots get defined in a hierarchical structure of specialized dicts, thus:
```
-- pyTRSplat.LotDefDB - dict, keyed by Twp/Rge (str), value-type:
---- pyTRSplat.TwpLotDefinitions - dict, keyed by sec number (int), value-type:
------ pyTRSplat.LotDefinitions - dict, keyed by lot name (ex: 'L2'), value-type:
-------- a string, being the name of one or more QQ's, separated by comma (ex: 'L2' -> 'NWNE')
```

Thus, rudimentary access in a `LotDefDB` object called `lddb_obj` might be `lddb_obj['154n97w'][1]['L2']` (using Python's built-in bracket syntax), perhaps resulting in `'NWNE'` (i.e. Lot 2, of Sec 1, T154N-R97W corresponds with the NW/4NE/4 of that section). *(See `pyTRSplat.LotDefDB` docs for specific getter methods that are designed to avoid key errors and handle defaults more robustly than Python's built-in `dict` methods/syntax.)*

However, the end user probably doesn't have much cause to directly access the contents of a `LotDefDB`, `TwpLotDefinitions` or `LotDefinitions` object. I suspect most users will only need to pass such objects as parameters for methods in `Plat` or `MultiPlat` objects, or potentially `SectionGrid` / `TownshipGrid` objects.

##### Loading `LotDefDB` data from .csv files (for use in `MultiPlat` and potentially `Plat` objects)


Any user who defines lots in a .csv and loads them with `from_csv=<filepath>` at init, probably won't need to interact with the contents of a `LotDefDB`, `TwpLotDefinitions`, or `LotDefinitions` object or understand their respective methods very deeply. Instead, they can most likely just pass a `LotDefDB` object to the `lddb=` parameter when initializing a `MultiPlat` object (or a `TwpLotDefinitions` object to the `tld=` parameter when initializing a `Plat` object).

*__[#TODO:__ Table for which objects / methods can take which lot definition types, and for which parameters.]*


```
import pyTRSplat

# This .csv file is included in the 'pyTRSplat\_examples\' directory. (May need to provide
# an absolute path, depending on where this code is being run.)
lddb_filepath = r'_examples\SAMPLE_LDDB.csv'




# Load the data from the .csv file into a LotDefDB object
lddb_obj_1 = pyTRSplat.LotDefDB(from_csv=lddb_filepath)
multiplat_1 = pyTRSplat.MultiPlat(settings='letter', lddb=lddb_obj_1)


# Load the relevant data (for T154N-R97W) from the .csv file into a TwpLotDefinitions object
# (twp/rge are mandatory here):
tld_obj_1 = pyTRSplat.TwpLotDefinitions.from_csv(lddb_filepath, twp='154n', rge='97w)

# and apply it to a Plat
plat_1 = pyTRSplat.Plat(settings='letter', tld=tld_obj, twp='154n', rge='97w')

# Alternatively, pull the TLD object out of `lddb_obj_1`, resulting in an equivalent
# TLD object. See section on 'Why lot definitions?' for the structure of LDDB objects.
tld_obj_2 = lddb_obj_1.get_tld('154n97w', allow_ld_defaults=False, force_)

```


When initializing a `pyTRSplat.LotDefDB` object, pass parameter `from_csv=<filepath>` to load data from a properly formatted\*\* .csv file.
```
# This example .csv file is included in the pyTRSplat/_examples/ dir. (May need to
# specify as an absolute path, depending on where this code is being run.)
lddb_filepath = r'pyTRSplat/_examples/SAMPLE_LDDB.csv'
lddb_obj = pyTRSplat.LotDefDB(from_csv=lddb_filepath)

# MultiPlat objects take LotDefDB objects natively in the `lddb=` init parameter:
multiplat_1 = pyTRSplat.MultiPlat(settings='letter', lddb=lddb_obj)


# Conversely, Plat objects are designed to take TwpLotDefinitions objects in the `tld=`
# init parameter. (TwpLotDefinitions objects are one level down in the lot definitions
# hierarchy -- i.e. the values stored in a LotDefDB object).

# Here, we extract a TLD from the LDDB we just created from the .csv file.
tld_obj_154n97w = lddb_obj.get_tld('154n97w')
plat_1 = pyTRSplat.Plat(twp='154n', rge='97w', settings='letter', tld=tld_obj_154n97w)

# However, if we have specified the Twp/Rge appropriately when initializing the Plat
# object, we can also pass the LotDefDB itself object to `tld=` (without first pulling
# the TLD), and the Plat itself will extract the appropriate TwpLotDefinitions object.
plat_2 = pyTRSplat.Plat(twp='154n', rge='97w', settings='letter', tld=lddb_obj)


# We can also load TLD objects from .csv file directly (Twp/Rge is mandatory):
tld_obj_2 = pyTRSplat.TwpLotDefinitions.from_csv(lddb_filepath, twp='154n', rge='97w')
```



##### Loading `TwpLotDefinitions` data from .csv files (for use in `Plat` objects)
```
# This example .csv file is included in the pyTRSplat/_examples/ dir. (May need to
# specify as an absolute path, depending on where this code is being run.)
lddb_filepath = r'pyTRSplat/_examples/SAMPLE_LDDB.csv'

# Load only the data relevant to T154N-R97W (since a TwpLotDefinitions object covers
# only a single Twp/Rge):
tld_obj_1 = pyTRSplat.TwpLotDefinitions.from_csv(lddb_filepath, twp='154n', rge='97w')

# Equivalently, load the .csv data into a LotDefDB object, and pull the
# TwpLotDefinitions object from that
lddb_obj = pyTRSplat.LotDefDB(from_csv=lddb_filepath)
tld_obj_2 = lddb_obj.get_tld('154n97w')
```


###### Formatting a .csv file for lot definitions
\*\* For proper .csv formatting, follow these guidelines (and see the example `SAMPLE_LDDB.csv` in the `'pyTRSplat\_examples\'` directory):
1) These 5 headers MUST exist, all lowercase: `twp`, `rge`, `sec`, `lot`, `qq`
2) twp must be specified in the format '000x' (up to 3 digits, plus N/S specified as a single, lowercase character 'n' or 's').
ex: `154n` for Township 154 North; `1s` for Township 7 South
3) rge must be specified in the format '000x' (up to 3 digits, plus E/W specified as a single, lowercase character 'e' or 'w').
ex: `97w` for Range 97 West; `6e` for Range 6 East
4) `sec` and `lot` should specified as simple integers (non-numeric lots cannot currently be handled)
5) `qq` should be in the format as follows:
    a) `NENE` for 'Northeast Quarter of the Northeast Quarter';
       `W2` for 'West Half'; `ALL` for 'ALL' ... (These get passed through `pyTRS` parsing, so reasonable abbreviations SHOULD be captured...)
    b) If a lot comprises more than a single QQ, separate QQs by comma (with no space), and/or use larger aliquot divisions as appropriate.
        ex: Lot 1 that comprises the N/2NE/4 could be specified under the 'qq' columns as `N2NE`
        ex: Lot 4 that sprawls across the E/2NW/4 and SW/4NW/4 could be specified under the 'qq' column as `E2NW,SWNW`
6) Any other columns (e.g., `COMMENTS`) should be acceptable but will be ignored.
7) Duplicate lot entries will result in only the last-entered row being effective. If a lot comprises multiple QQ's, keep it on a single row, and refer to list item #5 above on how to handle it.
8) Keep in mind that extra long .csv files might conceivably take a while to process and/or result in a LotDefDB that burdens the system's memory.



### Manual platting with `SectionGrid` and `TownshipGrid` objects, and other methods.

These objects are mostly beyond the scope of a quick-start guide, except to point you in the right direction:
* `pyTRSplat.TownshipGrid` -- A grid representing an entire township (i.e. a 6x6 grid of sections; and storing a `SectionGrid` object for each section)

* `pyTRSplat.SectionGrid` -- A grid representing a section (i.e. a 4x4 grid of quarter-quarters, or 'QQs')

Look into the respective documentation on these objects for how to manipulate / access their data. (Notably, when platting `pyTRS.Tract` and `pyTRS.PLSSDesc` objects, that data gets translated into these object types behind the scenes.)

Note that `TownshipGrid` and `SectionGrid` objects can be added to `PlatQueue` and `MultiPlatQueue` objects with `.queue_add()`; and both can be platted directly onto a `Plat` object with `.plat_township_grid()` and `.plat_sec_grid()`, respectively. (But to process them into a `MultiPlat` object, they must be added to a `MultiPlatObject`, which will be processed instead).

Also, for the simplest option for manual platting, look into the `Plat.fill_qq()` method, which does not use much logic beyond using the designated color to fill in the square at the designated grid coordinate for the designated section.


### Misc. functions / utilities:

These functions are also beyond the scope of a quick-start guide, and why they might be useful:
* `pyTRSplat.filter_tracts_by_twprge()` -- Filter a list of `pyTRS.Tract` objects into a dict, keyed by Twp/Rge
* `pyTRSplat.tracts_into_twp_grids()` -- Apply the parsed data in a list of `pyTRS.Tract` objects into a dict of TownshipGrid objects (keyed by Twp/Rge)
* `pyTRSplat.plssdesc_to_twp_grids()` -- Apply the parsed data in a `pyTRS.PLSSDesc` object into a dict of TownshipGrid objects (keyed by Twp/Rge)

I expect few users would have cause to use these functions without an already deep understanding of the whole module (so probably nobody).

###


```
import pyTRSplat

# The PLSS description of the land we want to plat.
land_description = 'T154N-R97W Sec 14: NE/4, Sec 15: W/2, Sec 22: Lot 1, S/2NE/4'

# This .csv file is included in the pyTRSplat\_examples\ directory. It
# defines what lot 1 means in Section 22, T154N-R97W (and other
# lots/sections).
lot_database_fp = r'_examples\SAMPLE_LDDB.csv'

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

