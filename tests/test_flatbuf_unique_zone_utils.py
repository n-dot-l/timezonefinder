"""
Unit tests for the unique_zone_utils module.
"""

import os
import tempfile
from pathlib import Path
from typing import Dict

import numpy as np
import pytest

from timezonefinder.flatbuf.unique_zone_utils import (
    write_unique_zones_flatbuffers,
    read_unique_zones_binary,
)


class TestUniqueZoneUtils:
    """Test cases for unique_zone_utils functions."""

    @pytest.mark.parametrize(
        "unique_zone_mapping",
        [
            {123: 1},
            {456: 4, 789: 7},
            {101112: 10, 101113: 11, 101114: 12},
            {},  # Empty dictionary
        ],
    )
    def test_write_read_unique_zones_roundtrip(
        self, unique_zone_mapping: Dict[int, int]
    ):
        """
        Test that writing unique zone entries to a file and reading them back
        preserves the data (round-trip test).
        """
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_path = Path(temp_file.name)

        try:
            # Write the unique zones to the temporary file
            write_unique_zones_flatbuffers(unique_zone_mapping, temp_path)

            # Check that the file exists and has content
            assert os.path.exists(temp_path)
            assert os.path.getsize(temp_path) > 0

            # Read the unique zones back
            result = read_unique_zones_binary(temp_path)

            # Verify the result
            assert len(result) == len(unique_zone_mapping)

            for hex_id, zone_id in unique_zone_mapping.items():
                assert hex_id in result
                assert result[hex_id] == zone_id

        finally:
            # Clean up the temporary file
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_read_unique_zones_binary_with_empty_file(self):
        """Test reading from an empty or invalid file raises an appropriate exception."""
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_path = Path(temp_file.name)

        try:
            # Try reading from the empty file
            with pytest.raises(Exception):  # Flatbuffers will raise an exception for invalid format
                read_unique_zones_binary(temp_path)
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_read_unique_zones_binary_with_nonexistent_file(self):
        """Test reading from a non-existent file raises FileNotFoundError."""
        non_existent_path = Path("/path/that/does/not/exist/unique_zones.fbs")

        with pytest.raises(FileNotFoundError):
            read_unique_zones_binary(non_existent_path)

    @pytest.mark.parametrize(
        "hex_id,zone_id",
        [
            (0, 0),  # Minimal case
            (2**32 - 1, 2**16 - 1),  # Maximum uint32 hex_id, maximum uint16 zone_id
            (42, 100),  # Typical values
        ],
    )
    def test_write_read_specific_values(self, hex_id: int, zone_id: int):
        """Test with specific boundary values to ensure correct handling."""
        unique_zone_mapping = {hex_id: zone_id}

        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_path = Path(temp_file.name)

        try:
            write_unique_zones_flatbuffers(unique_zone_mapping, temp_path)
            result = read_unique_zones_binary(temp_path)

            assert hex_id in result
            assert result[hex_id] == zone_id
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_large_data_handling(self):
        """Test with a larger dataset to ensure performance and memory handling."""
        # Create a larger dictionary with many entries
        large_mapping = {i: i % 100 for i in range(1000)}

        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_path = Path(temp_file.name)

        try:
            write_unique_zones_flatbuffers(large_mapping, temp_path)
            result = read_unique_zones_binary(temp_path)

            assert len(result) == len(large_mapping)

            # Check a sample of the results
            for i in range(0, 1000, 100):
                if i in large_mapping:
                    assert result[i] == large_mapping[i]
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
