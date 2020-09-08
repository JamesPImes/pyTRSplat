# Copyright (c) 2020, James P. Imes. All rights reserved.

"""Testing"""

from pyTRS.pyTRS import PLSSDesc, Tract
from grid import TownshipGrid, SectionGrid
from grid import LotDefinitions, TwpLotDefinitions, LotDefDB
from platsettings import Settings
from platqueue import PlatQueue, MultiPlatQueue
from plat import text_to_plats, Plat, MultiPlat

########################################################################
# Examples / Testing:
########################################################################
#
# The filepath to a .csv that can be read into a LotDefDB object:
example_lddb_filepath = r'C:\Users\James Imes\Box\Programming\pyTRS_plotter\assets\examples\SAMPLE_LDDB.csv'


# Creating a LotDefDB object by reading in a .csv file.
example_lddb_obj = LotDefDB.from_csv(example_lddb_filepath)
# Equivalently (because `.from_csv()` is implied when we pass a proper filepath to a .csv file):
example_lddb_obj = LotDefDB(example_lddb_filepath)


# Sample PLSS description text:
descrip_text = 'T154N-R97W Sec 01: Lots 1 - 3, S2NE, Sec 25: Lots 1 - 8, T155N-R97W Sec 22: W/2'


# Generating a list of plat images from `descrip_text` string:
ttp = text_to_plats(descrip_text, config='cleanQQ', lddb=example_lddb_filepath, settings='letter')
#ttp[0].show()  # Display the first image in the list (i.e. 154n97w in this case)

# Or as a MultiPlat object:
mp = MultiPlat.from_text(descrip_text, config='cleanQQ', lddb=example_lddb_filepath, settings='letter')
#mp.show(0)  # Display the first image in the MultiPlat (i.e. 154n97w in this case)



# Some miscellaneous objects that can be added to a PQ (or possibly MPQ):
t1 = Tract('154n97w14', 'NE/4', initParseQQ=True)
t2 = Tract('154n97w15', 'W/2', initParseQQ=True)
t3 = Tract('154n97w01', 'Lots 1 - 3, S2NE', initParseQQ=True)
t4 = Tract('154n97w25', 'Lots 4, 5, 7, NE4NE4', initParseQQ=True)
# PLSSDesc objects can only be added to MPQ objects, not to PQ objects.
d1 = PLSSDesc('T154N-R97W Sec 3: Lots 1, 4, S2N2, T155N-R97W Sec 18: Lots 2 - 4, E2W2', initParseQQ=True)
sg1 = SectionGrid.from_tract(t1)
tg1 = TownshipGrid('154n', '97w')
tg1.incorporate_tract(t2, 15)


# Generating a (single) Plat by adding objects to its PlatQueue (via `.queue()` method)
# and then processing the queue:
set1 = Settings.preset('letter')
sp = Plat(settings=set1, tld=example_lddb_obj['154n97w'])
sp.queue(sg1, t1)
sp.queue(tg1, t2)
sp.queue(t3)
sp.process_queue()


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
descrip_text1 = 'T154N-R97W Sec 01: Lots 1 - 3, S2NE, Sec 25: Lots 1 - 8, T155N-R97W Sec 22: W/2'
descrip_text2 = 'T154N-R97W Sec 14: NE/4'
mp4 = MultiPlat(settings='letter', lddb=example_lddb_obj)
mp4.queue_text(descrip_text1, config='cleanQQ')
mp4.queue_text(descrip_text2, config='cleanQQ')
mp4.process_queue()
#mp4.show(0)  # Show the first plat (i.e. 154n97w, in this case)