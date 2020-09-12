# Copyright (c) 2020, James P. Imes. All rights reserved.

"""Testing"""

from pyTRS.pyTRS import PLSSDesc, Tract
from grid import TownshipGrid, SectionGrid, LotDefinitions, TwpLotDefinitions, LotDefDB
from grid import tracts_into_twp_grids
from platsettings import Settings
from platqueue import PlatQueue, MultiPlatQueue
from plat import text_to_plats, Plat, MultiPlat

########################################################################
# Examples / Testing:
########################################################################
#

# Test handling of flawed pyTRS parses (due to erroneous PLSS descriptions)
# Force a parse that will result in a 'TRerr'
er_desc_1 = PLSSDesc(
    'Sec 14: NE/4, T155N-R97W Sec 15: NW/4',
    initParseQQ=True, config='TRS_desc')
# And a parse that will result in a 'secError'
er_desc_2 = PLSSDesc(
    'T154N-R97W The NE/4 of Section',
    initParseQQ=True, config='TR_desc_S')
test_dict_1 = tracts_into_twp_grids(er_desc_1.parsedTracts)
test_dict_2 = tracts_into_twp_grids(er_desc_2.parsedTracts)
#print(test_dict_1['TRerr'].sections[0].output_array())
#print(test_dict_1['TRerr'].sections[14].output_array())  # -> prints array for sec 14
#print(test_dict_2['154n97w'].sections[0].output_array())  # -> prints array for error 'sec 0'

mp_error_test_1 = MultiPlat.from_plssdesc(er_desc_1)
#mp_error_test_1.show(0)

mp_error_test_2 = MultiPlat.from_plssdesc(er_desc_2)
#mp_error_test_2.show(0)


# The filepath to a .csv that can be read into a LotDefDB object:
example_lddb_filepath = r'assets/examples/SAMPLE_LDDB.csv'

# Creating a LotDefDB object by reading in a .csv file.
example_lddb_obj = LotDefDB(from_csv=example_lddb_filepath)

# Sample PLSS description text:
descrip_text_1 = '''T154N-R97W
Sec 01: Lots 1 - 3, S2NE
Sec 25: Lots 1 - 8
Sec 26: Testing tract obj that contains no items in .lotList / .QQList
T155N-R97W Sec 22: W/2'''


# Generating a list of plat images from `descrip_text_1` string:
ttp = text_to_plats(
    descrip_text_1, config='cleanQQ', lddb=example_lddb_filepath, settings='letter')
ttp[0].show()  # Display the first image in the list (i.e. 154n97w in this case)

# Or as a MultiPlat object:
mp = MultiPlat.from_text(
    descrip_text_1, config='cleanQQ', lddb=example_lddb_filepath, settings='letter')
#mp.show(0)  # Display the first image in the MultiPlat (i.e. 154n97w in this case)

# If creating more than one MultiPlat object (or other class or function that takes
# `lddb=` as an argument), then it's probably better practice to create a LotDefDB
# object and pass that to `lddb=` -- rather than passing the filepath to `lddb=`.
# Creating the LDDB object first would avoid a lot of repetitive I/O and redundant
# objects in memory.


# Some miscellaneous objects that can be added to a PQ (or possibly MPQ):
t1 = Tract('154n97w14', 'NE/4', initParseQQ=True)
t2 = Tract('154n97w15', 'W/2', initParseQQ=True)
t3 = Tract('154n97w01', 'Lots 1 - 3, S2NE', initParseQQ=True)
t4 = Tract('154n97w25', 'Lots 4, 5, 7, NE4NE4', initParseQQ=True)
# PLSSDesc objects can only be added to MPQ objects -- not to PQ objects.
d1 = PLSSDesc(
    'T154N-R97W Sec 3: Lots 1, 4, S2N2, T155N-R97W Sec 18: Lots 2 - 4, E2W2',
    initParseQQ=True)
sg1 = SectionGrid.from_tract(t1)
tg1 = TownshipGrid('154n', '97w')
tg1.incorporate_tract(t2, 15)


# Generating a (single) Plat by adding objects to its PlatQueue (via
# `.queue()` method) and then processing the queue:
set1 = Settings(preset='letter')
sp = Plat(settings=set1, twp='154n', rge='97w', tld=example_lddb_obj['154n97w'])
sp.queue(sg1, t1)
sp.queue(tg1, t2)
sp.queue(t3)
sp.process_queue()

# Writing custom text on the Plat object we just created.
sp.write_custom_text('Testing custom 1')  # Continues writing where tracts left off.
sp.write_custom_text('Testing custom 2', cursor='new_cursor')
sp.write_custom_text('Testing custom 3', cursor='new_cursor')
# This next call uses cursor='text_cursor' (the default), which is still where
# `.new_cursor` was when writing 'Testing custom 2':
sp.write_custom_text('This will overwrite the "custom 2" line')
# Moving `.new_cursor` to a different coord:
sp.new_cursor = (340, 1900)
sp.write_custom_text('But this one should be off on its own', cursor='new_cursor')
#sp.show()


# Create a Settings object from the 'letter' preset, but adjust a few
# settings -- because we'll use it to create a single-section Plat from
# Tract `t1`.
custom_set2 = Settings(preset='letter')
custom_set2.qq_side = 240
custom_set2.centerbox_wh = 300
custom_set2.secfont_size = 72
custom_set2.tractfont_size = 48
custom_set2._update_fonts()  # Won't create the ImageFont objects if we don't do this
sp2 = Plat.from_tract(t1, settings=custom_set2, single_sec=True)
#sp2.show()


# Demonstrating adding objects to MultiPlatQueue, and then generating a
# MultiPlat from that MPQ.
mpq_obj = MultiPlatQueue()
mpq_obj.queue(sg1, '154n97w', t1)
mpq_obj.queue(tg1, '154n97w', t2)
mpq_obj.queue(t3, '154n97w')
mpq_obj.queue(d1)

# Note that feeding the filepath to `lddb=` will create the LotDefDB
# object (by reading from file) when this MultiPlat is created.
mp1 = MultiPlat.from_queue(mpq_obj, settings='letter', lddb=example_lddb_filepath)
#mp1.show(0)  # Show the first plat (i.e. 154n97w, in this case)

# Or equivalently, creating a MultiPlat object, and processing an
# (external) MultiPlatQueue object...
mp2 = MultiPlat(settings='letter', lddb=example_lddb_filepath)
mp2.process_queue(mpq_obj)
#mp2.show(0)  # Show the first plat (i.e. 154n97w, in this case)


# Demonstrating adding objects to MultiPlat.mpq via `.queue()`, and then
# processing the queue.
# Note that passing the already-created LotDefDB object to `lddb=` does
# NOT create a new LDDB obj when this MultiPlat object is created.
mp3 = MultiPlat(settings='letter', lddb=example_lddb_obj)
mp3.queue(sg1, '154n97w', t1)
mp3.queue(tg1, '154n97w', t2)
mp3.queue(t3, '154n97w')
mp3.queue(d1)
mp3.process_queue()
#mp3.show(0)  # Show the first plat (i.e. 154n97w, in this case)


# Demonstrating adding text to a MultiPlat queue (`config=` is optional,
# and just affects how the text is parsed by the pyTRS module):
descrip_text_2 = '''T154N-R97W Sec 01: Lots 1 - 3, S2NE, Sec 25: Lots 1 - 8,
T155N-R97W Sec 22: W/2'''
descrip_text_3 = 'T154N-R97W Sec 14: NE/4'
mp4 = MultiPlat(settings='letter', lddb=example_lddb_obj)
mp4.queue_text(descrip_text_2, config='cleanQQ')
mp4.queue_text(descrip_text_3, config='cleanQQ')
mp4.process_queue()
#mp4.show(0)  # Show the first plat (i.e. 154n97w, in this case)