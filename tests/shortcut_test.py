"""
test the actually stored shortcut binary file
"""

import h3.api.numpy_int as h3
import numpy as np
import pytest

from scripts import file_converter
from scripts.utils import (
    check_shortcut_sorting,
    has_coherent_sequences,
)
from timezonefinder.configs import SHORTCUT_H3_RES
from timezonefinder.flatbuf.shortcut_utils import (
    get_shortcut_file_path,
    read_shortcuts_binary,
)
from timezonefinder.flatbuf.unique_shortcut_utils import (
    get_unique_shortcut_file_path,
    read_unique_shortcuts_binary,
)
from timezonefinder.timezonefinder import TimezoneFinder
from timezonefinder.utils_numba import int2coord

shortcut_file_path = get_shortcut_file_path()
shortcuts = read_shortcuts_binary(shortcut_file_path)

try:
    unique_shortcut_file_path = get_unique_shortcut_file_path()
    unique_shortcuts = read_unique_shortcuts_binary(unique_shortcut_file_path)
except FileNotFoundError:
    # Handle case where file might not exist during certain test setups
    unique_shortcuts = {}


VERBOSE_TESTING = True


def latlng_to_cell(lng: float, lat: float) -> int:
    return h3.latlng_to_cell(lat, lng, SHORTCUT_H3_RES)


@pytest.fixture
def tf():
    return TimezoneFinder(in_memory=True)


def test_shortcut_completeness(tf):
    """Test that all points of each polygon are included in the proper shortcuts."""
    # Get access to the timezone polygons
    errors = []
    for poly_id in range(tf.nr_of_polygons):
        poly = tf.boundaries.coords_of(poly_id)
        if poly.shape[1] == 0:
            # this polygon's geometry has been deleted, skip checks
            continue

        if VERBOSE_TESTING and poly_id % 100 == 0:
            print(f"\rvalidating polygon {poly_id}", end="", flush=True)

        for i, pt in enumerate(poly.T):
            # ATTENTION: int to coord conversion required!
            lng = int2coord(pt[0])
            lat = int2coord(pt[1])
            hex_id = latlng_to_cell(lng, lat)
            try:
                shortcut_entries = shortcuts[hex_id]
            except KeyError:
                errors.append(
                    f"shortcut mapping is incomplete at point ({lng}, {lat}) "
                    f"(hexagon cell id {hex_id} missing in mapping)"
                )
                continue

            if poly_id not in shortcut_entries:
                errors.append(
                    f"point #{i} ({lng}, {lat}) of polygon {poly_id} "
                    f"does not appear in shortcut entries {shortcut_entries} of cell {hex_id}"
                )

    assert not errors, f"Shortcut completeness errors: {errors[:5]}"


def test_shortcut_resolution():
    """Test that all shortcuts have the correct H3 resolution."""
    invalid_resolutions = []
    for hex_id in shortcuts.keys():
        res = h3.get_resolution(hex_id)
        if res != SHORTCUT_H3_RES:
            invalid_resolutions.append(
                f"Hexagon {hex_id} has resolution {res}, expected {SHORTCUT_H3_RES}"
            )

    assert not invalid_resolutions, f"Resolution errors: {invalid_resolutions[:5]}"


def test_unused_polygons(tf):
    """Test that all polygons are used in at least one shortcut."""
    # Get the total number of polygons
    nr_of_polygons = tf.nr_of_polygons

    # check if all polygons are used in the shortcuts
    used_polygons = set()
    for poly_ids in shortcuts.values():
        used_polygons.update(poly_ids)

    all_polygon_ids = set(range(nr_of_polygons))
    unused_poly_ids = all_polygon_ids - used_polygons

    assert len(unused_poly_ids) == 0, (
        f"There are {len(unused_poly_ids)} unused polygons: {list(unused_poly_ids)[:5]}"
    )


def test_empty_shortcut():
    """Test that no shortcut entries are empty (all should have polygons)."""
    # since using timezone data with ocean coverage all the cells should have polygons in them
    empty_shortcuts = []
    for hex_id, polygon_ids in shortcuts.items():
        if len(polygon_ids) == 0:
            boundary = h3.cell_to_boundary(hex_id)[0]
            empty_shortcuts.append(f"Hexagon {hex_id} at {boundary}")

    assert not empty_shortcuts, f"Found empty shortcut entries: {empty_shortcuts[:5]}"


def test_unique_pole_cells():
    """Test that exactly one cell surrounds each pole."""
    s_pole_cells = []
    n_pole_cells = []

    for hex_id in shortcuts.keys():
        hex = file_converter.get_hex(hex_id)
        if hex.surr_s_pole:
            s_pole_cells.append(hex_id)
        if hex.surr_n_pole:
            n_pole_cells.append(hex_id)

    assert len(s_pole_cells) == 1, (
        f"{len(s_pole_cells)} cells surround the south pole: {s_pole_cells}"
    )
    assert len(n_pole_cells) == 1, (
        f"{len(n_pole_cells)} cells surround the north pole: {n_pole_cells}"
    )


def test_shortcut_uniqueness():
    """Test that shortcuts are unique (no duplicates in polygon IDs)."""
    duplicates = []
    for hex_id, polygon_ids in shortcuts.items():
        if len(np.unique(polygon_ids)) != len(polygon_ids):
            duplicates.append(
                f"Shortcut {hex_id} contains duplicate polygon IDs: {polygon_ids}"
            )

    assert not duplicates, f"Shortcut uniqueness errors: {duplicates[:5]}"


@pytest.mark.parametrize(
    "lst,expected",
    [
        ([], True),
        ([1], True),
        ([1, 1], True),
        ([2, 3], True),
        ([2, 3, 3, 0, 0, 4], True),
        ([2, 3, 2], False),
        ([2, 3, 2, 3], False),
    ],
)
def test_has_coherent_check_fct(lst, expected):
    assert has_coherent_sequences(lst) == expected


def test_shortcut_sorting(tf):
    """Test that shortcuts are correctly sorted by zone ID and polygon size."""
    invalid_sortings = []
    for hex_id, polygon_ids in shortcuts.items():
        try:
            check_shortcut_sorting(polygon_ids, tf.zone_ids)
        except AssertionError as e:
            invalid_sortings.append(f"Invalid sorting for hexagon {hex_id}: {str(e)}")

    assert not invalid_sortings, f"Shortcut sorting errors: {invalid_sortings[:5]}"


def test_unique_shortcuts_correctness(tf):
    """
    Test that every unique shortcut points to a zone that is the only zone in the corresponding main shortcut.
    """
    if not unique_shortcuts:
        pytest.skip("No unique shortcuts file found to test.")

    errors = []
    for hex_id, unique_zone_id in unique_shortcuts.items():
        try:
            poly_ids_in_shortcut = shortcuts[hex_id]
        except KeyError:
            errors.append(
                f"Hexagon {hex_id} from unique shortcuts not found in main shortcuts."
            )
            continue

        if not poly_ids_in_shortcut.size > 0:
            errors.append(
                f"Hexagon {hex_id} from unique shortcuts is empty in main shortcuts."
            )
            continue

        zone_ids = np.unique(tf.zone_ids_of(poly_ids_in_shortcut))
        if len(zone_ids) > 1:
            errors.append(
                f"Hexagon {hex_id} in unique shortcuts should only have one zone, but has {len(zone_ids)}: {zone_ids}."
            )
        elif zone_ids[0] != unique_zone_id:
            errors.append(
                f"Hexagon {hex_id} has mismatched zone id. Unique shortcut has {unique_zone_id}, main shortcut has {zone_ids[0]}."
            )

    assert not errors, f"Unique shortcut correctness errors: {errors[:5]}"


def test_unique_shortcut_resolution():
    """Test that all unique shortcuts have the correct H3 resolution."""
    if not unique_shortcuts:
        pytest.skip("No unique shortcuts file found to test.")

    invalid_resolutions = []
    for hex_id in unique_shortcuts.keys():
        res = h3.get_resolution(hex_id)
        if res != SHORTCUT_H3_RES:
            invalid_resolutions.append(
                f"Hexagon {hex_id} has resolution {res}, expected {SHORTCUT_H3_RES}"
            )

    assert not invalid_resolutions, f"Resolution errors: {invalid_resolutions[:5]}"
