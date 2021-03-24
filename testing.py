# Copyright (c) 2020, James P. Imes. All rights reserved.

"""Testing"""

from pytrs import PLSSDesc, Tract

from pytrsplat.grid import TownshipGrid, SectionGrid, LotDefinitions, TwpLotDefinitions, LotDefDB
from pytrsplat.grid import tracts_into_twp_grids
from pytrsplat.platsettings import Settings
from pytrsplat.platqueue import PlatQueue, MultiPlatQueue
from pytrsplat.plat import Plat, MultiPlat
from pytrsplat.plat import text_to_plats


########################################################################
# Examples / Testing:
########################################################################
#
TESTING_DIR = 'testing\\'

from pathlib import Path
from datetime import datetime
t = datetime.now()
timestamp = (
    f"{t.year}{str(t.month).rjust(2, '0')}{str(t.day).rjust(2, '0')}"
    f"_{str(t.hour).rjust(2, '0')}{str(t.minute).rjust(2, '0')}"
    f"{str(t.second).rjust(2, '0')}"
)

TESTING_DIR = f"{TESTING_DIR}\\{timestamp}\\"
Path(TESTING_DIR).mkdir(parents=True, exist_ok=True)

i = 0

# Test handling of flawed pytrs parses (due to erroneous PLSS descriptions)
# Force a parse that will result in a 'TRerr'
er_desc_1 = PLSSDesc(
    'Sec 14: NE/4, T155N-R97W Sec 15: NW/4',
    parse_qq=True, config='TRS_desc')
# And a parse that will result in a 'secError'
er_desc_2 = PLSSDesc(
    'T154N-R97W The NE/4 of Section',
    parse_qq=True, config='TR_desc_S')
test_dict_1 = tracts_into_twp_grids(er_desc_1.tracts)
test_dict_2 = tracts_into_twp_grids(er_desc_2.tracts)
# print(test_dict_1['TRerr'].sections[0].output_array())
# print(test_dict_1['TRerr'].sections[14].output_array())  # prints array for sec 14
# print(test_dict_2['154n97w'].sections[0].output_array())  # prints array for error 'sec 0'

mp_error_test_1 = MultiPlat.from_plssdesc(er_desc_1)
#mp_error_test_1.show(0)
mp_error_test_1.output_to_png(f"{TESTING_DIR}\\{str(i).rjust(3, '0')}_mp_error_test_1.png")
i += 1

mp_error_test_2 = MultiPlat.from_plssdesc(er_desc_2)
#mp_error_test_2.show(0)
mp_error_test_2.output_to_png(f"{TESTING_DIR}\\{str(i).rjust(3, '0')}_mp_error_test_2.png")
i += 1


# The filepath to a .csv that can be read into a LotDefDB object:
example_lddb_filepath = r'pytrsplat/_examples/SAMPLE_LDDB.csv'

# Creating a LotDefDB object by reading in a .csv file.
example_lddb_obj = LotDefDB(from_csv=example_lddb_filepath)
print(f"Imported LDDB data:\n{example_lddb_obj}\n\n")

# Sample PLSS description text:
descrip_text_1 = '''T154N-R97W
Sec 01: Lots 1 - 3, S2NE
Sec 25: Lots 1 - 8
Sec 26: Testing tract obj that contains no items in .lots / .qqs
T155N-R97W Sec 22: W/2'''
d = PLSSDesc(descrip_text_1, parse_qq=True)
t = d.tracts[0]
p = Plat(settings='letter')
p.queue_add(t)
p.process_queue()
#p.show()
p.output(f"{TESTING_DIR}\\{str(i).rjust(3, '0')}_single_plat_by_process_"
         f"queue_and_unhandled_lots.png")
i += 1

mp = MultiPlat(settings='letter')
mp.queue_add(d)
mp.process_queue()
#mp.show(0)
print(f"For description:\n{descrip_text_1}\n\n...these lots were not defined:")
print(mp.all_unhandled_lots)
mp.output_to_png(f"{TESTING_DIR}\\{str(i).rjust(3, '0')}_mp_unhandled_lots.png")
i += 1

# Generating a list of plat images from `descrip_text_1` string:
ttp = text_to_plats(
    descrip_text_1, config='clean_qq', lddb=example_lddb_filepath, settings='letter')
#ttp[0].show()  # Display the first image in the list (i.e. 154n97w in this case)
ttp[0].save(f"{TESTING_DIR}\\{str(i).rjust(3, '0')}_ttp_from_unparsed_text.png")
i += 1


# Or as a MultiPlat object:
mp = MultiPlat.from_unparsed_text(
    descrip_text_1, config='clean_qq', lddb=example_lddb_filepath, settings='letter')
#mp.show(0)  # Display the first image in the MultiPlat (i.e. 154n97w in this case)
mp.output_to_png(f"{TESTING_DIR}\\{str(i).rjust(3, '0')}_mp_from_unparsed_text.png")
i += 1

# If creating more than one MultiPlat object (or other class or function that takes
# `lddb=` as an argument), then it's probably better practice to create a LotDefDB
# object and pass that to `lddb=` -- rather than passing the filepath to `lddb=`.
# Creating the LDDB object first would avoid a lot of repetitive I/O and redundant
# objects in memory.


# Some miscellaneous objects that can be added to a PQ (or possibly MPQ):
t1 = Tract('NE/4', '154n97w14', parse_qq=True)
t2 = Tract('W/2', '154n97w15', parse_qq=True)
t3 = Tract('Lots 1 - 3, S2NE', '154n97w01', parse_qq=True)
t4 = Tract('Lots 4, 5, 7, NE4NE4', '154n97w25', parse_qq=True)
# PLSSDesc objects can only be added to MPQ objects -- not to PQ objects.
d1 = PLSSDesc(
    'T154N-R97W Sec 3: Lots 1, 4, S2N2, T155N-R97W Sec 18: Lots 2 - 4, E2W2',
    parse_qq=True)
sg1 = SectionGrid.from_tract(t1)
tg1 = TownshipGrid('154n', '97w')
tg1.incorporate_tract(t2, 15)


# Generating a (single) Plat by adding objects to its PlatQueue (via
# `.queue_add()` method) and then processing the queue_add:
set1 = Settings(preset='letter')
sp = Plat(settings=set1, twp='154n', rge='97w', tld=example_lddb_obj['154n97w'])
sp.queue_add(sg1, t1)
sp.queue_add(tg1, t2)
sp.queue_add(t3)
sp.process_queue()

# Writing custom text on the Plat object we just created.
sp.text_box.write_line('Testing custom 1')  # Continues writing where tracts left off.
sp.text_box.write_line('Testing custom 2', cursor='other_cursor')
sp.text_box.write_line('Testing custom 3', cursor='other_cursor')
# This next call uses cursor='text_cursor' (the default), which is still where
# `.other_cursor` was when writing 'Testing custom 2':
sp.text_box.write_line('This will overwrite the "custom 2" line')
# Moving `.other_cursor` to a different coord:
sp.text_box.set_cursor((370, 240), 'other_cursor')
# equivalently:
sp.text_box.other_cursor = (370, 240)
sp.text_box.write_line('But this one should be off on its own', cursor='other_cursor')
#sp.show()
sp.output(f"{TESTING_DIR}\\{str(i).rjust(3, '0')}_custom_text_write.png")
i += 1


# Create a Settings object from the 'letter' preset, but adjust a few
# settings -- because we'll use it to create a single-section Plat from
# Tract `t1`.
custom_set2 = Settings(preset='letter')
custom_set2.qq_side = 240
custom_set2.centerbox_wh = 300

# Setting a variable to the filepath of the bold/italicized version of
# the included 'Liberation Sans' font.
boldital_tf = Settings.TYPEFACES['Sans-Serif (Bold-Italic)']

# Using size 72 font and a lighter color (RGBA), but the original
# typeface, to write sec numbers:
custom_set2.set_font('sec', size=72, RGBA=(200, 200, 200, 255))

# Using size 48 font and the bold/italics typeface to write tracts (color unchanged):
custom_set2.set_font('tract', size=48, typeface=boldital_tf)

# Using the bold/italics typeface to write the header (but using the same size as before)
custom_set2.set_font('header', typeface=boldital_tf)

# Create a Plat object from Tract object `t1`, using our custom settings,
# and plating it as only a single section
sp2 = Plat.from_tract(t1, settings=custom_set2, single_sec=True)
#sp2.show()
sp2.output(f"{TESTING_DIR}\\{str(i).rjust(3, '0')}_custom_settings.png")
i += 1


# Demonstrating adding objects to MultiPlatQueue, and then generating a
# MultiPlat from that MPQ.
mpq_obj = MultiPlatQueue()
mpq_obj.queue_add(sg1, '154n97w', t1)
mpq_obj.queue_add(tg1, '154n97w', t2)
mpq_obj.queue_add(t3, '154n97w')
mpq_obj.queue_add(d1)

# Note that feeding the filepath to `lddb=` will create the LotDefDB
# object (by reading from file) when this MultiPlat is created.
mp1 = MultiPlat.from_queue(mpq_obj, settings='letter', lddb=example_lddb_filepath)
#mp1.show(0)  # Show the first plat (i.e. 154n97w, in this case)
mp1.output_to_png(f"{TESTING_DIR}\\{str(i).rjust(3, '0')}_from_mpq.png")
i += 1

# Or equivalently, creating a MultiPlat object, and processing an
# (external) MultiPlatQueue object...
mp2 = MultiPlat(settings='letter', lddb=example_lddb_filepath)
mp2.process_queue(mpq_obj)
#mp2.show(0)  # Show the first plat (i.e. 154n97w, in this case)
mp2.output_to_png(f"{TESTING_DIR}\\{str(i).rjust(3, '0')}_process_mpq.png")
i += 1

# Demonstrating adding objects to MultiPlat.mpq via `.queue_add()`, and then
# processing the queue_add.
# Note that passing the already-created LotDefDB object to `lddb=` does
# NOT create a new LDDB obj when this MultiPlat object is created.
mp3 = MultiPlat(settings='letter', lddb=example_lddb_obj)
mp3.queue_add(sg1, '154n97w', t1)
mp3.queue_add(tg1, '154n97w', t2)
mp3.queue_add(t3, '154n97w')
mp3.queue_add(d1)
mp3.process_queue()
#mp3.show(0)  # Show the first plat (i.e. 154n97w, in this case)
mp3.output_to_png(f"{TESTING_DIR}\\{str(i).rjust(3, '0')}_queue_mpq_then_process.png")
i += 1

# Demonstrating adding text to a MultiPlat queue_add (`config=` is optional,
# and just affects how the text is parsed by the pytrs module):
descrip_text_2 = '''T154N-R97W Sec 01: Lots 1 - 3, S2NE, Sec 25: Lots 1 - 8,
T155N-R97W Sec 22: W/2'''
descrip_text_3 = 'T154N-R97W Sec 14: NE/4'
mp4 = MultiPlat(settings='letter', lddb=example_lddb_obj)
mp4.queue_add_text(descrip_text_2, config='clean_qq')
mp4.queue_add_text(descrip_text_3, config='clean_qq')
mp4.process_queue()
#mp4.show(0)  # Show the first plat (i.e. 154n97w, in this case)
mp4.output_to_png(f"{TESTING_DIR}\\{str(i).rjust(3, '0')}_add_text_mpq.png")
i += 1


# Testing writing too many tracts than can fit in our plat.
dx = PLSSDesc('T154N-R97W Sec 1 - 17: NE/4SW/4, NW/4SE/4', parse_qq=True)
pqx = PlatQueue()
for tr in dx.tracts:
    pqx.queue_add(tr)
tx = Tract(
    (
        'That portion of the NE/4 lying in the '
        "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do "
        "eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim "
        "ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut "
        "aliquip ex ea commodo consequat. Duis aute irure dolor in "
        "reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla "
        "pariatur. Excepteur sint occaecat cupidatat non proident, sunt in "
        "culpa qui officia deserunt mollit anim id est laborum."
    ), trs='154n97w18', parse_qq=True)
pqx.queue_add(tx)
sp3 = Plat.from_queue(pqx, twp='154n', rge='97w', settings='letter')

sp3.output(f"{TESTING_DIR}\\{str(i).rjust(3, '0')}_tract_text_too_long.png")
i += 1


input(f"Success: {TESTING_DIR}")