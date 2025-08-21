import pytrsplat

land_description = "T8S-R58W, Sec 1: Lot 1, E/2 of Lot 2, S/2N/2, Sec 2: E/2, Sec 11: ALL"

# If we didn't specify Twp/Rge here, it would be added when we add the first tract.
plat = pytrsplat.Plat(twp='8s', rge='58w')
# Use preset settings, but modify it to write lot numbers.
plat.settings = pytrsplat.Settings.preset('default')
plat.settings.write_lot_numbers = True
# Assume 'standard' 80-acre lots (in sections along north and west of township)
plat.lot_definer.allow_defaults = True
# For this Twp/Rge, we assume lots are standardized to 80 acres, common in parts of Colorado.
plat.lot_definer.standard_lot_size = 80

# Add the above land description, using the specified pytrs config string.
# NOTE: If we tried to add lands outside of T8S-R58W, this would raise a ValueError.
# If we need to plat lands across township boundaries, use a PlatGroup or MegaPlat instead.
plat.add_description(land_description, config='n,w')

plat.execute_queue()
# Output the results, and save them to a PNG. (Could also create .PDF, .TIFF, etc.).
only_image = plat.output(
    fp=r'./results/example_plat_results.png',
)

# View the result in whichever app is your default image viewer.
only_image.show()
