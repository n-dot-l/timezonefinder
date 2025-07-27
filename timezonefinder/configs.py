# settings, can be overridden in scripts/configs.py for data generation
# resolution of the h3 hexagons
# DON'T CHANGE THIS WITHOUT CAREFUL CONSIDERATION!
# h3 resolution used for polygon embedding and for the shortcuts
# the higher the resolution, the more memory is needed for the shortcuts
H3_RESOLUTION: int = 6

# files names of the packaged data
HOLES_FILE_NAME = "holes.json"
# name of the flatbuffer file for the boundaries
# (.fbs is the file extension for flatbuffer schema files)
POLYGON_FILE_NAME = "coordinates.fbs"
SHORTCUTS_FILE_NAME = "shortcuts.fbs"
HEX_ZONES_FILE_NAME = "hex_zones.fbs"
TIMEZONE_NAMES_FILE_NAME = "timezone_names.txt"
ZONE_IDS_FILE_NAME = "zone_ids.npy"
ZONE_POSITIONS_FILE_NAME = "zone_positions.npy"
HOLE_REGISTRY_FILE_NAME = "hole_registry.json"

# BBoxes of the polygons are stored in these files
# BBOX_X_MAX_FILE_NAME = "max_x.re"
# BBOX_X_MIN_FILE_NAME = "min_x.re"
# BBOX_Y_MAX_FILE_NAME = "max_y.re"
# BBOX_Y_MIN_FILE_NAME = "min_y.re"

# the most common timezone names (=zones)
# a list of tz names is compiled in the data generation process
# for all tz with id < NR_SHORTCUT_ZONE_IDS a shortcut is created
# this means that for all coordinates inside the BBox of such a zone, the correct tz is returned right away
# NR_SHORTCUT_ZONE_IDS = 10

# when a zone is split up into unconnected polygons, those get assigned the same name (=id)
# the most common zone name is "uninhabited"
# all the polygons of the uninhabited zones are not used for timezone finding, but for theAdmin boundary queries
# they are mostly water areas within countries.
# it is not distinguished between different uninhabited zones.
# UNINHABITED_ZONE_ID = 0