import argparse
from pathlib import Path

import numpy as np

from timezonefinder.configs import DEFAULT_DATA_DIR
from timezonefinder.flatbuf.hex_zone_mapping_utils import (
    get_hex_zone_mapping_file_path,
    write_hex_zone_mapping_flatbuffers,
)
from timezonefinder.flatbuf.shortcut_utils import read_shortcuts_binary, get_shortcut_file_path
from timezonefinder.np_binary_helpers import (
    get_zone_ids_path,
    read_per_polygon_vector,
)


def create_hex_zone_mapping(data_dir: Path):
    """
    Creates a mapping from H3 hexagon IDs to unique timezone zone IDs for all hexagons
    that contain polygons of only one timezone.
    This mapping is then stored in a flatbuffer file.
    """
    print("Creating hex to unique zone mapping...")
    shortcut_path = get_shortcut_file_path(data_dir)
    shortcut_mapping = read_shortcuts_binary(shortcut_path)

    zone_ids_path = get_zone_ids_path(data_dir)
    zone_ids_vector = read_per_polygon_vector(zone_ids_path)

    hex_zone_mapping = {}
    for hex_id, poly_ids in shortcut_mapping.items():
        if poly_ids.size == 0:
            continue

        zone_ids = zone_ids_vector[poly_ids]
        unique_zones = np.unique(zone_ids)
        if len(unique_zones) == 1:
            # All polygons in this hexagon belong to the same zone
            hex_zone_mapping[hex_id] = unique_zones[0]

    output_file = get_hex_zone_mapping_file_path(data_dir)
    write_hex_zone_mapping_flatbuffers(
        hex_zone_mapping=hex_zone_mapping, output_file=output_file
    )
    print("...done.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Create a mapping from H3 hexagon IDs to unique timezone zone IDs."
    )
    parser.add_argument(
        "-out",
        "--output-dir",
        type=str,
        default=str(DEFAULT_DATA_DIR),
        help="The directory where the data files are located and the output file will be saved.",
    )
    args = parser.parse_args()
    data_path = Path(args.output_dir)
    create_hex_zone_mapping(data_path)