#!/usr/bin/env python
# coding=utf-8
"""
This script reads the timezone data from a geojson file and converts it into the binary formats for this library.

The script is a huge monolith and is kept that way to make it easy to copy and paste.
External libraries are only used for parsing the data.
The created binary files are completely self-contained and do not have any dependencies.
Python ^3.9 is required to run this script.

The oceans data file can be downloaded from:
https://github.com/evansiroky/timezone-boundary-builder/releases/latest/download/timezones-with-oceans.geojson.zip
The land only data file can be downloaded from:
https://github.com/evansiroky/timezone-boundary-builder/releases/latest/download/timezones.geojson.zip

The required geojson file is called "combined-with-oceans.json" or "combined.json"

A big thanks to Eric Muller for providing the timezone boundary data.
A big thanks to Adam h. sivil f. for the h3-py library.
"""

import argparse
from pathlib import Path
from typing import Dict, List, Set, Tuple
from geojson import Feature, FeatureCollection, Polygon
import numpy as np
import h3

from timezonefinder.configs import (
    INT2COORD_FACTOR,
    MAX_LAT,
    MAX_LNG,
    MIN_LAT,
    MIN_LNG,
    NR_BYTES_BBOX,
    NR_BYTES_H_IDX,
    NR_BYTES_INDEX,
    NR_BYTES_MAIN_IDX,
    NR_BYTES_SHIFT,
    SHORTCUT_H3_RES,
)
from timezonefinder.flatbuf.polygon_utils import (
    get_boundaries_file_path,
    get_holes_file_path,
    write_polygon_flatbuffers,
)
from timezonefinder.flatbuf.shortcut_utils import (
    get_shortcut_file_path,
    write_shortcuts_flatbuffers,
)
from timezonefinder.flatbuf.unique_zone_utils import (
    get_unique_zone_file_path,
    write_unique_zones_flatbuffers,
)
from timezonefinder.utils import (
    get_boundaries_dir,
    get_hole_registry_path,
    get_holes_dir,
    get_timezone_names_path,
    get_zone_ids_path,
    get_zone_positions_path,
    poly_to_wkb,
    coord2int,
    get_last_change_idx,
)
from timezonefinder.zone_names import write_zone_names
import json

# from timezonefinder import command_line as cli
from scripts.reporter import Reporter, log_time, time

# only used for parsing the data.
# active environment must have "geojson", "numpy" and "shapely" installed
# pip install "h3>=3.7.6,<4" geojson "numpy>=1.23.5,<2" "shapely>=2.0.1,<3"


def get_coords_from_polygon(polygon: Polygon) -> List:
    return list(polygon.exterior.coords)


def signed_area(coords: List[Tuple[float, float]]) -> float:
    """
    Return the signed area of the polygon.
    The signed area is positive if the vertices are in counter-clockwise order and negative if they are in clockwise order.
    The algorithm is based on the Shoelace formula.
    https://en.wikipedia.org/wiki/Shoelace_formula
    """
    area = 0.0
    for i in range(len(coords) - 1):
        x1, y1 = coords[i]
        x2, y2 = coords[i + 1]
        area += x1 * y2 - x2 * y1
    return area / 2.0


def is_clockwise(coords: List[Tuple[float, float]]) -> bool:
    """
    Check if the vertices of a polygon are in clockwise order.
    """
    return signed_area(coords) < 0


def get_h3_shortcuts(
    polygons: List[np.ndarray], polygon_zones_ids: List[int], n_polygons: int
) -> Dict[int, List[int]]:
    """
    Calculate the H3 shortcuts for a list of polygons.
    A shortcut is a mapping from an H3 hexagon ID to a list of polygon IDs that are contained in that hexagon.
    The resolution of the H3 hexagons is defined by ``SHORTCUT_H3_RES``.
    A polygon is considered to be contained in a hexagon if its centroid is within the hexagon.

    :param polygons: A list of polygons, where each polygon is represented by a NumPy array of coordinates.
    :param polygon_zones_ids: A list of zone IDs, where each ID corresponds to a polygon in the ``polygons`` list.
    :param n_polygons: The total number of polygons.
    :return: A dictionary mapping H3 hexagon IDs to lists of polygon IDs.
    """
    print(f"building h3 shortcuts of resolution {SHORTCUT_H3_RES}")
    # Create a dictionary to store the shortcuts
    shortcut_mapping: Dict[int, List[int]] = {}

    # Iterate over all polygons
    for polygon_id in range(n_polygons):
        # Get the polygon coordinates and zone ID
        polygon = polygons[polygon_id]
        zone_id = polygon_zones_ids[polygon_id]

        # Convert the polygon to a WKB representation and create a Shapely polygon object
        # Use shapely for centroid calculation and to check if a point is within the polygon
        # This is more robust than the previous implementation
        wkb_polygon = poly_to_wkb(polygon, is_3d=False)
        from shapely import from_wkb, Polygon

        shapely_polygon: Polygon = from_wkb(wkb_polygon)

        # Get the set of H3 hexagon IDs that are contained in the polygon
        # Convert the polygon to a GeoJSON-like dictionary
        geo_json_polygon = {
            "type": "Polygon",
            "coordinates": [
                [[x / INT2COORD_FACTOR, y / INT2COORD_FACTOR] for x, y in polygon]
            ],
        }
        hex_ids_in_polygon: Set[int] = h3.polygon_to_cells(
            geo_json_polygon, SHORTCUT_H3_RES
        )

        # Add the polygon ID to the shortcut mapping for each hexagon
        for hex_id in hex_ids_in_polygon:
            if hex_id not in shortcut_mapping:
                shortcut_mapping[hex_id] = []
            shortcut_mapping[hex_id].append(polygon_id)

    # sort the polygons in each shortcut by zone id and then by size
    # this is important for the performance of the timezone finding algorithm
    # since it checks the polygons in order and stops at the first match
    for hex_id in shortcut_mapping:
        shortcut_mapping[hex_id].sort(
            key=lambda polygon_id: (
                polygon_zones_ids[polygon_id],
                -len(polygons[polygon_id]),
            )
        )
    return shortcut_mapping


@log_time
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Converts the geojson timezone data into the binary formats used by this library."
    )
    parser.add_argument(
        "-inp",
        "--input_file",
        type=str,
        required=True,
        help="The path to the combined-with-oceans.json file.",
    )
    parser.add_argument(
        "-out",
        "--output_path",
        type=str,
        required=True,
        help="The path to the output folder where the binary files should be stored.",
    )
    parser.add_argument(
        "-r",
        "--reporter",
        type=str,
        default=None,
        help="The path to the output folder where the report file should be stored.",
    )

    args = parser.parse_args()
    input_file = Path(args.input_file)
    output_path = Path(args.output_path)
    output_path.mkdir(exist_ok=True)
    reporter = Reporter() if args.reporter else None

    with open(input_file, encoding="utf-8") as f:
        print(f"loading data from {input_file}")
        geojson_data: FeatureCollection = FeatureCollection(json.load(f))

    print(f"{len(geojson_data.features)} polygons found.")
    polygons: List[np.ndarray] = []
    poly_zone_ids: List[int] = []
    holes: List[np.ndarray] = []
    hole_zone_ids: List[int] = []
    # a dict mapping each boundary polygon to its holes
    # key: polygon_id, value: list of hole ids
    hole_registry: Dict[int, List[int]] = {}
    timezone_names: List[str] = []

    n_features = len(geojson_data.features)

    for i, feature in enumerate(geojson_data.features):
        feature: Feature = feature
        tz_name = feature.properties["tzid"]
        if tz_name not in timezone_names:
            timezone_names.append(tz_name)
        zone_id = timezone_names.index(tz_name)

        # on the top level there are the polygons of the boundaries
        # the first ring is the polygon itself, all others are holes
        for p, polygon_coords_list in enumerate(feature.geometry.coordinates):
            # check if the polygon is a hole
            # the first polygon is never a hole
            is_hole = p > 0

            # shapely detects the geometry type automatically
            # a polygon with only one ring is a polygon without holes
            # a polygon with more than one ring is a polygon with holes
            coords = polygon_coords_list
            if is_hole:
                # check if the hole is clockwise, if not, reverse it
                if not is_clockwise(coords):
                    coords.reverse()
                holes.append(
                    np.array(
                        [
                            (coord2int(lng), coord2int(lat))
                            for lng, lat in coords
                        ],
                        dtype=np.int32,
                    )
                )
                hole_zone_ids.append(zone_id)
                # register the hole to the last boundary polygon
                hole_registry[len(polygons) - 1].append(len(holes) - 1)

            else:
                # check if the polygon is counter-clockwise, if not, reverse it
                if is_clockwise(coords):
                    coords.reverse()
                polygons.append(
                    np.array(
                        [
                            (coord2int(lng), coord2int(lat))
                            for lng, lat in coords
                        ],
                        dtype=np.int32,
                    )
                )
                poly_zone_ids.append(zone_id)
                hole_registry[len(polygons) - 1] = []

    print(f"{len(timezone_names)} unique timezone names found.")
    assert max(poly_zone_ids) == len(timezone_names) - 1
    assert len(polygons) == len(poly_zone_ids)
    assert len(holes) == len(hole_zone_ids)

    n_polygons = len(polygons)
    n_holes = len(holes)
    print(f"{n_polygons} boundary polygons found.")
    print(f"{n_holes} holes found.")

    if reporter:
        reporter.add_stat("Number of polygons", n_polygons)
        reporter.add_stat("Number of holes", n_holes)
        reporter.add_stat("Number of timezones", len(timezone_names))

    # ZONE ID MAPPING
    # write the zone ids for each polygon to a file
    # this is a mapping from polygon_id to zone_id
    # the index of the list is the polygon_id
    print(f"writing {n_polygons} zone ids to file")
    zone_ids_path = get_zone_ids_path(output_path)
    np.array(poly_zone_ids, dtype=np.uint16).tofile(zone_ids_path)

    # TIMEZONE NAMES
    # write the timezone names to a file
    # the index of the list is the zone_id
    print(f"writing {len(timezone_names)} timezone names to file")
    path = get_timezone_names_path(output_path)
    write_zone_names(timezone_names, path)

    # sort the polygons by zone id and then by size
    # this is important for the performance of the timezone finding algorithm
    # since it checks the polygons in order and stops at the first match
    print("sorting polygons by zone id and then by size")
    combined = list(zip(polygons, poly_zone_ids))
    combined.sort(key=lambda x: (x[1], -len(x[0])))
    polygons, poly_zone_ids = zip(*combined)
    polygons = list(polygons)
    poly_zone_ids = list(poly_zone_ids)

    # create a mapping from old polygon ids to new polygon ids
    # to update the hole registry
    print("updating hole registry")
    old_polygon_ids = [i for i, _ in sorted(enumerate(combined), key=lambda x: x[1])]
    new_polygon_ids = {old_id: new_id for new_id, old_id in enumerate(old_polygon_ids)}
    new_hole_registry = {}
    for old_polygon_id, hole_ids in hole_registry.items():
        new_polygon_id = new_polygon_ids[old_polygon_id]
        new_hole_registry[new_polygon_id] = hole_ids
    hole_registry = new_hole_registry

    # create a list of the first polygon of each zone
    # this is used to quickly find all polygons of a zone
    print("creating zone positions index")
    zone_positions = [0] * (len(timezone_names) + 1)
    for i in range(n_polygons - 1, -1, -1):
        zone_positions[poly_zone_ids[i]] = i
    zone_positions[-1] = n_polygons
    assert zone_positions[0] == 0
    assert get_last_change_idx(np.array(poly_zone_ids)) == zone_positions[-2]

    # write the zone positions to a file
    print(f"writing {len(zone_positions)} zone positions to file")
    path = get_zone_positions_path(output_path)
    np.array(zone_positions, dtype=np.uint32).tofile(path)

    # for all holes belonging to a polygon, their ids are consecutive
    # -> only the id of the first hole and the number of holes have to be stored for each polygon
    hole_registry_path = get_hole_registry_path(output_path)
    hole_registry_tmp: Dict[int, Tuple[int, int]] = {}
    for polygon_id in sorted(hole_registry.keys()):
        hole_ids = hole_registry[polygon_id]
        if len(hole_ids) > 0:
            # check if the hole ids are consecutive
            for i in range(len(hole_ids) - 1):
                assert hole_ids[i] + 1 == hole_ids[i + 1]
            hole_registry_tmp[polygon_id] = (hole_ids[0], len(hole_ids))

    print(f"writing {len(hole_registry_tmp)} hole registry entries to file")
    with open(hole_registry_path, "w", encoding="utf-8") as f:
        json.dump(hole_registry_tmp, f)

    boundaries_dir = get_boundaries_dir(output_path)
    boundaries_dir.mkdir(exist_ok=True)
    holes_dir = get_holes_dir(output_path)
    holes_dir.mkdir(exist_ok=True)

    print("writing boundaries to flatbuffer")
    boundaries_path = get_boundaries_file_path(boundaries_dir)
    write_polygon_flatbuffers(polygons, boundaries_path)

    print("writing holes to flatbuffer")
    holes_path = get_holes_file_path(holes_dir)
    write_polygon_flatbuffers(holes, holes_path)

    # SHORTCUTS
    shortcut_mapping = get_h3_shortcuts(polygons, poly_zone_ids, n_polygons)
    path = get_shortcut_file_path(output_path)
    write_shortcuts_flatbuffers(shortcut_mapping, path)
    if reporter:
        reporter.add_stat("Number of shortcuts", len(shortcut_mapping))

    # UNIQUE ZONE SHORTCUTS
    # pre-compute a mapping from hex_id to zone_id for all hexagons that only contain polygons of one timezone
    unique_zone_mapping = {}
    n_unique = 0
    for hex_id, poly_ids in shortcut_mapping.items():
        if not poly_ids:
            continue
        first_zone_id = poly_zone_ids[poly_ids[0]]
        is_unique = all(poly_zone_ids[p_id] == first_zone_id for p_id in poly_ids)
        if is_unique:
            unique_zone_mapping[hex_id] = first_zone_id
            n_unique += 1

    path = get_unique_zone_file_path(output_path)
    write_unique_zones_flatbuffers(unique_zone_mapping, path)
    print(f"{n_unique} unique zone shortcuts found ({n_unique / len(shortcut_mapping) * 100:.2f}% of all shortcuts)")
    if reporter:
        reporter.add_stat("Number of unique zone shortcuts", n_unique)
        reporter.add_stat(
            "Percentage of unique zone shortcuts",
            f"{n_unique / len(shortcut_mapping) * 100:.2f}%",
        )

    # create a data report
    if reporter:
        report_path = Path(args.reporter)
        report_path.mkdir(exist_ok=True)
        reporter.write_report(report_path)


if __name__ == "__main__":
    main()
