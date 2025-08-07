"""
Unit tests for the shortcut_utils module.
"""

import os
import tempfile
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pytest

from timezonefinder.configs import NO_UNIQUE_ZONE # Import NO_UNIQUE_ZONE
from timezonefinder.flatbuf.shortcut_utils import (
    write_shortcuts_flatbuffers,
    read_shortcuts_binary,
)


class TestShortcutUtils:
    """Test cases for shortcut_utils functions."""

    @pytest.mark.parametrize(
        "shortcut_mapping_input",
        [
            {123: ([1, 2, 3], NO_UNIQUE_ZONE)},
            {456: ([4, 5, 6], 10), 789: ([7, 8, 9], NO_UNIQUE_ZONE)},
            {101112: ([10, 11, 12, 13, 14], 20)},
            {},  # Empty dictionary
        ],
    )
    def test_write_read_shortcuts_roundtrip(
        self, shortcut_mapping_input: Dict[int, Tuple[List[int], int]]
    ):
        """
        Test that writing shortcuts to a file and reading them back
        preserves the data (round-trip test).
        """
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_path = Path(temp_file.name)

        try:
            # Write the shortcuts to the temporary file
            write_shortcuts_flatbuffers(shortcut_mapping_input, temp_path)

            # Check that the file exists and has content
            assert os.path.exists(temp_path)
            assert os.path.getsize(temp_path) > 0

            # Read the shortcuts back
            result = read_shortcuts_binary(temp_path)

            # Verify the result
            assert len(result) == len(shortcut_mapping_input)

            for hex_id, (poly_ids_expected, unique_zone_id_expected) in shortcut_mapping_input.items():
                assert hex_id in result
                poly_ids_actual, unique_zone_id_actual = result[hex_id]
                np.testing.assert_array_equal(
                    poly_ids_actual, np.array(poly_ids_expected, dtype=np.uint16)
                )
                assert unique_zone_id_actual == unique_zone_id_expected

        finally:
            # Clean up the temporary file
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_read_shortcuts_binary_with_empty_file(self):
        """Test reading from an empty or invalid file raises an appropriate exception."""
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_path = Path(temp_file.name)

        try:
            # Try reading from the empty file
            with pytest.raises(Exception):
                read_shortcuts_binary(temp_path)
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_read_shortcuts_binary_with_nonexistent_file(self):
        """Test reading from a non-existent file raises an appropriate exception."""
        non_existent_path = Path("/path/that/does/not/exist/shortcuts.fbs")

        with pytest.raises(FileNotFoundError):
            read_shortcuts_binary(non_existent_path)

    @pytest.mark.parametrize(
        "hex_id,poly_ids,unique_zone_id",
        [
            (0, [0], NO_UNIQUE_ZONE),  # Minimal case
            (2**32 - 1, list(range(10)), 100),  # Maximum uint32 with multiple polygons and a unique zone
            (42, list(range(100)), NO_UNIQUE_ZONE),  # Many polygon IDs
            (1000, [], 5), # Empty poly_ids, but unique zone
        ],
    )
    def test_write_read_specific_values(self, hex_id: int, poly_ids: List[int], unique_zone_id: int):
        """Test with specific boundary values to ensure correct handling."""
        shortcut_mapping = {hex_id: (poly_ids, unique_zone_id)}

        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_path = Path(temp_file.name)

        try:
            write_shortcuts_flatbuffers(shortcut_mapping, temp_path)
            result = read_shortcuts_binary(temp_path)

            assert hex_id in result
            poly_ids_actual, unique_zone_id_actual = result[hex_id]
            np.testing.assert_array_equal(
                poly_ids_actual, np.array(poly_ids, dtype=np.uint16)
            )
            assert unique_zone_id_actual == unique_zone_id
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_large_data_handling(self):
        """Test with a larger dataset to ensure performance and memory handling."""
        # Create a larger dictionary with many entries, some with unique_zone_id
        large_mapping = {
            i: (list(range(i % 10, i % 10 + 5)), i % 2 == 0 and i % 10 < 5 and i % 10 or NO_UNIQUE_ZONE)
            for i in range(1000)
        }

        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_path = Path(temp_file.name)

        try:
            write_shortcuts_flatbuffers(large_mapping, temp_path)
            result = read_shortcuts_binary(temp_path)

            assert len(result) == len(large_mapping)

            # Check a sample of the results
            for i in range(0, 1000, 100):
                if i in large_mapping:  # Just to be safe
                    poly_ids_expected, unique_zone_id_expected = large_mapping[i]
                    poly_ids_actual, unique_zone_id_actual = result[i]
                    np.testing.assert_array_equal(
                        poly_ids_actual, np.array(poly_ids_expected, dtype=np.uint16)
                    )
                    assert unique_zone_id_actual == unique_zone_id_expected
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
