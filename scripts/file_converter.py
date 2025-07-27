#!/usr/bin/env python
# coding=utf-8
import json
from argparse import ArgumentParser
from collections import Counter
from pathlib import Path
from typing import Dict, List, Tuple

from scripts.configs import (
    DATA_DIR,
    OCEAN_GEOMETRY_FILE,
    PARSED_FILES_DIR,
    TIMEZONE_GEOMETRY_FILE,
    TIMEZONE_NAMES_FILE,
)
from scripts.reporting import write_data_report
from scripts.utils import (
    H3Converter,
    feature_from_geojson,
    get_last_modified_date,
    poly_from_list,
    sort_polygons,
    percent,
)
from timezonefinder.configs import (
    H3_RESOLUTION,
    HOLE_REGISTRY_FILE_NAME,
    TIMEZONE_NAMES_FILE_NAME,
    ZONE_IDS_FILE_NAME,
    ZONE_POSITIONS_FILE_NAME,
)
from timezonefinder.file_converter_util import (
    coord_list_to_coord_array,
    create_hole_data,
    create_polygon_data,
    get_all_coords,
    get_polygon_table,
    prepare_polygons,
    save_poly_zone_ids,
    save_timezone_names,
    save_zone_positions,
)
from timezonefinder.flatbuf.shortcut_utils import (
    create_shortcut_data,
    get_shortcut_file_path,
)

# for the statistics:
all_tz_names = []
poly_zone_ids = []
polynrs_of_holes = []  # list of the polygon nrs of all holes
all_hole_lengths = []


def get_tz_names_from_file() -> List[str]:
    with open(TIMEZONE_NAMES_FILE, "r") as f:
        return json.load(f)


def tz_names_are_equal(tz_names_in_file, tz_names_in_mem):
    return Counter(tz_names_in_file) == Counter(tz_names_in_mem)


def get_unique_tz_names(tz_names_in_mem: List[str]) -> List[str]:
    # a list of all unique timezone names (str)
    return sorted(list(set(tz_names_in_mem)))


def compile_holes(
    list_of_polygons, list_of_hole_nrs: List[int], min_nr_of_vertices: int = 4
) -> Tuple[List, List[int]]:
    global polynrs_of_holes, all_hole_lengths
    all_holes = []
    # a list of all hole polygon numbers ("foreign keys" to the polygons)
    polynrs_of_holes = []
    for hole_nr in list_of_hole_nrs:
        hole_per_poly = list_of_polygons[hole_nr][1:]
        all_holes.extend(hole_per_poly)
        polynrs_of_holes.extend(len(hole_per_poly) * [hole_nr])

    print(f"there are {len(all_holes)} holes in total")

    all_holes, polynrs_of_holes = simplify_polygons(
        all_holes, min_nr_of_vertices, foreign_keys=polynrs_of_holes
    )

    all_hole_lengths = [len(hole) for hole in all_holes]
    return all_holes, polynrs_of_holes


def compile_boundaries(
    list_of_polygons, list_of_boundary_nrs, min_nr_of_vertices=4
):
    all_boundaries = [list_of_polygons[i][0] for i in list_of_boundary_nrs]

    all_boundaries, _ = simplify_polygons(
        all_boundaries, min_nr_of_vertices, keep_empty_polygons=False
    )
    polygon_lengths = [len(p) for p in all_boundaries]

    # Attention: from here on the order of the polygons is changed!
    print("sorting boundaries...")
    # sort the polygons by the x value of their first coordinate
    # this makes the search for the right polygon faster
    all_boundaries, polygon_lengths = sort_polygons(all_boundaries, polygon_lengths)

    return all_boundaries, polygon_lengths


def get_oceans_and_tz_data(
    json_path: Path,
) -> Tuple[List, List, List, List[str]]:
    global all_tz_names, poly_zone_ids
    print(f"opening {json_path}")

    oceans, timezones, list_of_polygons = feature_from_geojson(json_path)

    timezone_names = get_unique_tz_names([d["name"] for d in timezones])
    print(f"found {len(timezone_names)} unique timezones")
    print(f"found {len(list_of_polygons)} polygons in total")
    all_tz_names.extend(timezone_names)

    # a list of all polygon numbers which are holes
    list_of_hole_nrs = []
    # a list of all polygon numbers which are boundaries
    list_of_boundary_nrs = []
    # list of all timezone numbers ("foreign keys") of all polygons
    poly_zone_ids = [None] * len(list_of_polygons)

    for i in range(len(list_of_polygons)):
        poly_props = list_of_polygons[i].properties
        tz_name = poly_props["tzid"]
        is_hole = poly_props["hole"]
        # id should be the list index of the polygons name in the list of all names
        tz_id = timezone_names.index(tz_name)
        poly_zone_ids[i] = tz_id

        if is_hole:
            list_of_hole_nrs.append(i)
        else:
            list_of_boundary_nrs.append(i)

    return oceans, list_of_polygons, list_of_hole_nrs, list_of_boundary_nrs


def main(inp, output_path: Path, keep_oceans: bool = False):
    global all_tz_names, poly_zone_ids, polynrs_of_holes, all_hole_lengths

    output_path.mkdir(exist_ok=True)
    PARSED_FILES_DIR.mkdir(exist_ok=True)

    json_path = Path(inp)
    if not json_path.exists() or not json_path.is_file():
        raise FileNotFoundError(f"the input file {json_path} does not exist")

    (
        oceans,
        list_of_polygons,
        list_of_hole_nrs,
        list_of_boundary_nrs,
    ) = get_oceans_and_tz_data(json_path)

    # transform the coordinates of all polygons and holes
    # create a coordinate array and lists of lists of all coordinates
    # polygons and holes are simplified, which means some of them are deleted.
    # The lists of foreign keys are adjusted accordingly
    all_polygons, polygon_lengths = compile_boundaries(
        list_of_polygons, list_of_boundary_nrs
    )
    nr_of_polygons = len(all_polygons)
    print(f"compiling {nr_of_polygons} polygons")

    # update the poly_zone_ids (some polygons have been deleted)
    poly_zone_ids = [
        x
        for x, p in zip(poly_zone_ids, list_of_polygons)
        if len(p.coords[0]) > 0 and not p.properties["hole"]
    ]
    # Attention: from here on the order of the polygons is changed!
    poly_zone_ids, _ = sort_polygons(poly_zone_ids)

    all_holes, polynrs_of_holes = compile_holes(list_of_polygons, list_of_hole_nrs)
    nr_of_holes = len(all_holes)
    print(f"compiling {nr_of_holes} holes")

    if keep_oceans:
        print("including ocean timezones...")
        # TODO implement proper merging of ocean data
        # simply append the ocean data to the existing data
        pass

    print("collecting all coordinates...")
    all_coords, coord_of_hole_exists = get_all_coords(all_polygons, all_holes)
    print("prepare polygons...")
    (
        poly_coord_first_val,
        poly_coord_last_val,
        poly_nr_of_coords,
        poly_hole_first_val,
        poly_hole_last_val,
        poly_nr_of_holes,
        hole_coord_first_val,
        hole_coord_last_val,
        hole_nr_of_coords,
        hole_registry,
    ) = prepare_polygons(
        all_polygons,
        all_holes,
        polynrs_of_holes,
        all_coords,
        coord_of_hole_exists,
    )
    print(f"there are {len(all_coords)} coordinates in total")

    # create the flatbuffer data for the polygons
    poly_data = get_polygon_table(
        all_polygons,
        all_coords,
        poly_coord_first_val,
        poly_coord_last_val,
        poly_nr_of_coords,
        poly_hole_first_val,
        poly_hole_last_val,
        poly_nr_of_holes,
        hole_coord_first_val,
        hole_coord_last_val,
        hole_nr_of_coords,
    )

    # list of all coordinates stored in one big array
    coord_array = coord_list_to_coord_array(all_coords)

    # create all the files in the output folder:
    print(f"writing data to {output_path}")

    # timezone names
    path = output_path / TIMEZONE_NAMES_FILE_NAME
    save_timezone_names(all_tz_names, path)
    nr_of_zones = len(all_tz_names)

    # polygon <-> zone mapping
    path = output_path / ZONE_IDS_FILE_NAME
    save_poly_zone_ids(poly_zone_ids, path)

    # pre-calculated zone bounding boxes
    path = output_path / ZONE_POSITIONS_FILE_NAME
    save_zone_positions(all_polygons, poly_zone_ids, all_tz_names, path)

    # polygon data
    create_polygon_data(poly_data, coord_array, output_path)

    # hole data
    create_hole_data(hole_registry, output_path)
    with open(output_path / HOLE_REGISTRY_FILE_NAME, "w") as f:
        json.dump(hole_registry, f)

    print("building shortcuts...")
    h3_converter = H3Converter(all_polygons, H3_RESOLUTION)
    shortcuts = h3_converter.compute_h3_shortcuts()
    print("shortcuts have been built.")

    print("separating unique zone shortcuts from multi-zone shortcuts...")
    unique_zone_hex_map: Dict[int, int] = {}
    multi_zone_shortcut_map: Dict[int, List[int]] = {}
    for h3_id, poly_ids in shortcuts.items():
        zone_ids_for_hex = {poly_zone_ids[p_id] for p_id in poly_ids}
        if len(zone_ids_for_hex) == 1:
            unique_zone_id = zone_ids_for_hex.pop()
            unique_zone_hex_map[h3_id] = unique_zone_id
        else:
            multi_zone_shortcut_map[h3_id] = poly_ids

    nr_unique = len(unique_zone_hex_map)
    nr_multi = len(multi_zone_shortcut_map)
    total = nr_unique + nr_multi
    if total > 0:
        print(
            f"shortcuts have been separated. {nr_unique} ({percent(nr_unique, total)}%) "
            f"of hexagons have a unique zone."
        )

    # create the flatbuffer files for the shortcuts
    from timezonefinder.flatbuf.hex_zone_utils import (
        create_hex_zone_data,
        get_hex_zone_file_path,
    )

    shortcut_path = get_shortcut_file_path(output_path)
    print(f"writing {len(multi_zone_shortcut_map)} shortcut entries to {shortcut_path}")
    create_shortcut_data(multi_zone_shortcut_map, shortcut_path)

    hex_zone_path = get_hex_zone_file_path(output_path)
    print(f"writing {len(unique_zone_hex_map)} unique zone entries to {hex_zone_path}")
    create_hex_zone_data(unique_zone_hex_map, hex_zone_path)

    print("writing data report...")
    write_data_report(
        multi_zone_shortcut_map,
        unique_zone_hex_map,
        output_path,
        nr_of_polygons,
        nr_of_zones,
        polygon_lengths,
        all_hole_lengths,
        polynrs_of_holes,
        poly_zone_ids,
        all_tz_names,
    )
    print("finished.")


if __name__ == "__main__":
    parser = ArgumentParser(
        description="This script reads timezone boundary data in geojson format and converts it into the binary"
        " format used by this package. It is not necessary to run this script as a user of this package.",
    )
    parser.add_argument(
        "-inp",
        "--input",
        dest="input_file",
        type=str,
        default=TIMEZONE_GEOMETRY_FILE,
        help="input geojson file",
    )
    parser.add_argument(
        "-out",
        "--output",
        dest="output_dir",
        type=str,
        default=DATA_DIR,
        help="output directory for the binary files",
    )
    parser.add_argument(
        "-oceans",
        dest="keep_oceans",
        action="store_true",
        default=False,
        help=f"Keep tz data for oceans from {OCEAN_GEOMETRY_FILE}. They are removed by default.",
    )

    args = parser.parse_args()
    print(f"Timezone data last modified: {get_last_modified_date(Path(args.input_file))}")
    main(args.input_file, Path(args.output_dir), args.keep_oceans)