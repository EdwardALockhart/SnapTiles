import os
import rasterio as rio
from rasterio.transform import from_gcps
from rasterio.control import GroundControlPoint



class GridException(Exception):
    pass

def inverse_mapping(letters_dict):
    inv = {}
    for x, y_dict in letters_dict.items():
        for y, letter in y_dict.items():
            inv[letter] = (x, y)
    return inv

def osgb_to_xy(coords):
    try:
        tile, ref_x, ref_y = coords.split()

        (x_maj, y_maj) = INV_MAJOR_LETTERS[tile[0]]
        (x_min, y_min) = INV_MINOR_LETTERS[tile[1]]

        assert len(ref_x) == len(ref_y) and len(ref_x) >= 1 and len(ref_x) <= 5
        coord_width = len(ref_x)
        multiplier = 10 ** (5 - coord_width)
        x_micro = int(ref_x) * multiplier
        y_micro = int(ref_y) * multiplier

    except (ValueError, IndexError, KeyError, AssertionError):
        raise GridException('Invalid format of coordinates')

    easting = x_maj*500000 + x_min*100000 + x_micro
    northing = y_maj*500000 + y_min*100000 + y_micro
    return (easting, northing)

MAJOR_LETTERS = {0: {0: 'S', 1: 'N', 2: 'H'},
                 1: {0: 'T', 1: 'O'}}
MINOR_LETTERS = {0: {0: 'V', 1: 'Q', 2: 'L', 3: 'F', 4: 'A'},
                 1: {0: 'W', 1: 'R', 2: 'M', 3: 'G', 4: 'B'},
                 2: {0: 'X', 1: 'S', 2: 'N', 3: 'H', 4: 'C'},
                 3: {0: 'Y', 1: 'T', 2: 'O', 3: 'J', 4: 'D'},
                 4: {0: 'Z', 1: 'U', 2: 'P', 3: 'K', 4: 'E'}}
INV_MAJOR_LETTERS = inverse_mapping(MAJOR_LETTERS)
INV_MINOR_LETTERS = inverse_mapping(MINOR_LETTERS)

def format_grid_reference(text):
    text = "".join(text.split())
    lengths = [2, 4, 6, 8, 10, 12]
    if len(text) not in lengths:
        return 'none'
    letters = text[:2]
    nums = text[2:]
    nums_first = nums[:int(len(nums)/2)]
    nums_second = nums[int(len(nums)/2):]
    final = letters + ' ' + nums_first + ' ' + nums_second
    return final



main_dir = "/OSMapTiles"
# Data are in "1_25K (All UK)"
# Output folder is "1_25K (All UK) Georeferenced"

for file in os.listdir(os.path.join(main_dir, "1_25K (All UK)")):
    
    # Read the image
    dataset = rio.open(os.path.join(main_dir, "1_25K (All UK)", file))

    # Get bottom left coordinates and extent
    name = file.split('.')[0]
    gridref = format_grid_reference(name).upper()
    (x, y) = osgb_to_xy(gridref)
    extent = int('100000'[:-len(gridref.split()[-1])])
    
    # Assign coordinates for each corner
    tl_cords = (x, y+extent)
    bl_cords = (x, y)
    br_cords = (x+extent, y) 
    tr_cords = (x+extent, y+extent)
    # Create control points
    tl = GroundControlPoint(0, 0, tl_cords[0], tl_cords[1])
    tr = GroundControlPoint(0, dataset.width, tr_cords[0], tr_cords[1])
    bl = GroundControlPoint(dataset.height, 0, bl_cords[0], bl_cords[1])
    br = GroundControlPoint(dataset.width, dataset.height, br_cords[0], br_cords[1])
    gcps = [tl, tr, bl, br]
    # Calculate the transformation and assign the coordinate system
    transform = from_gcps(gcps)
    crs = 'epsg:27700'
    
    # Write the file
    with rio.open(os.path.join(main_dir, "1_25K (All UK) Georeferenced", file), 'w',
                  driver = 'GTiff',
                  height = dataset.height,
                  width = dataset.width,
                  count = 1,
                  dtype = dataset.profile['dtype'],
                  crs = crs,
                  transform = transform,
                  compress = 'lzw') as dst:
        dst.write(dataset.read())
        dst.write_colormap(1, dataset.colormap(1))
