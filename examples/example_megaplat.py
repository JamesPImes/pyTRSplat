import pytrsplat

land_description = '''Township 154 North, Range 97 West
Section 1: Lots 1 - 3, S/2N/2
Section 5: Lot 4, The South Half of the Northwest Quarter, and The Southwest Quarter
Section 6: Lots 1 - 5, E/2 of Lots 6 and 7, S/2NE/4, SE/4NW/4, E/2SW/4, SE/4
Section 13: That portion of the E/2 lying north of the river and west of the private road right-of-way as more particularly described in Book 1234 / Page 567, recorded on January 1, 1964 in the records of Example County, as amended in that Right-of-Way Amendment Agreement dated December 10, 1987, recorded on December 11, 1987 as Document No. 1987-1234567 of the records of Example County.
Section 14: NE/4, NE/4NW/4, S/2NW/4NW/4
Section 29: Lots 1, 2, 3
Section 31: Lot 1, N/2NE/4, SE/4NE/4

Township 155 North, Range 97 West
Section 3: Lots 3, 4, S/2NW/4
Section 27: East 30 ft of the W/2

Township 156 North, Range 94 West
Section 4: ALL
'''

mega_plat = pytrsplat.MegaPlat()
# Use preset settings.
# Note: HIGHLY recommend using a 'megaplat_default' or 'megaplat_s'.
mega_plat.settings = pytrsplat.Settings.preset('megaplat_default')
# Load a lot definer from .csv f ile.
mega_plat.lot_definer.load_from_csv(r"sample_lot_definitions_154n97w.csv")
# Assume 'standard' 40-acre lots (in sections along north and west of township)
mega_plat.lot_definer.allow_defaults = True
mega_plat.lot_definer.standard_lot_size = 40

# Add the above land description, using the specified pytrs config string.
mega_plat.add_description(land_description, config='n,w')
mega_plat.execute_queue()
# Output the results, and save them to a PNG.
only_image = mega_plat.output(
    fp=r'./results/example_megaplat_results.png',
)

# View the result in whichever app is your default image viewer.
only_image.show()
