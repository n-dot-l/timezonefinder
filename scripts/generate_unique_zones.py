# new script to generate the unique zone shortcuts
import numpy as np
from timezonefinder.flatbuf.shortcut_utils import (
    get_shortcut_file_path,
    read_shortcuts_binary,
)
from timezonefinder.flatbuf.unique_zone_utils import (
    get_unique_zone_file_path,
    write_unique_zones_flatbuffers,
)
from timezonefinder.np_binary_helpers import (
    get_zone_ids_path,
    read_per_polygon_vector,
)
from scripts.configs import BINARY_FILE_DIR

print("creating unique zone mapping...")

# load existing data
shortcut_path = get_shortcut_file_path(BINARY_FILE_DIR)
shortcut_mapping = read_shortcuts_binary(shortcut_path)

zone_ids_path = get_zone_ids_path(BINARY_FILE_DIR)
zone_ids = read_per_polygon_vector(zone_ids_path)

# compute unique zone mapping
unique_zone_mapping = {}
for hex_id, poly_ids in shortcut_mapping.items():
    if len(poly_ids) == 0:
        continue
    
    p_zone_ids = zone_ids[poly_ids]
    unique_ids = np.unique(p_zone_ids)

    if len(unique_ids) == 1:
        unique_zone_mapping[hex_id] = unique_ids[0]

# write new mapping to file
output_path = get_unique_zone_file_path(BINARY_FILE_DIR)
write_unique_zones_flatbuffers(unique_zone_mapping, output_path)

print(f"unique zone mapping with {len(unique_zone_mapping)} entries has been created.")
