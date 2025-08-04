"""
Unit tests for the hex_zone_utils module.
"""

import os
import tempfile
from pathlib import Path
from typing import Dict

import pytest

from timezonefinder.flatbuf.hex_zone_utils import (
    write_hex_zone_flatbuffers,
    read_hex_zone_binary,
)


class TestHexZoneUtils:
    """Test cases for hex_zone_utils functions."""

    @pytest.mark.parametrize(
        "hex_zone_mapping",
        [
            {123: 1},
            {456: 4, 789: 7},
            {101112: 10},
            {},  # Empty dictionary
        ],
    )
    def test_write_read_hex_zone_roundtrip(self, hex_zone_mapping: Dict[int, int]):
        """
        Test that writing hex-zone mappings to a file and reading them back
        preserves the data (round-trip test).
        """
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_path = Path(temp_file.name)

        try:
            # Write the mappings to the temporary file
            write_hex_zone_flatbuffers(hex_zone_mapping, temp_path)

            # Check that the file exists and has content
            assert os.path.exists(temp_path)
            assert os.path.getsize(temp_path) > 0

            # Read the mappings back
            result = read_hex_zone_binary(temp_path)

            # Verify the result
            assert result == hex_zone_mapping

        finally:
            # Clean up the temporary file
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_read_hex_zone_binary_with_empty_file(self):
        """Test reading from an empty or invalid file raises an appropriate exception."""
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_path = Path(temp_file.name)

        try:
            # Try reading from the empty file
            with pytest.raises(Exception):
                read_hex_zone_binary(temp_path)
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_read_hex_zone_binary_with_nonexistent_file(self):
        """Test reading from a non-existent file raises an appropriate exception."""
        non_existent_path = Path("/path/that/does/not/exist/hex_zones.fbs")

        with pytest.raises(FileNotFoundError):
            read_hex_zone_binary(non_existent_path)

    @pytest.mark.parametrize(
        "hex_id,zone_id",
        [
            (0, 0),  # Minimal case
            (2**64 - 1, 65535),  # Maximum values for ulong and ushort
        ],
    )
    def test_write_read_specific_values(self, hex_id: int, zone_id: int):
        """Test with specific boundary values to ensure correct handling."""
        hex_zone_mapping = {hex_id: zone_id}

        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_path = Path(temp_file.name)

        try:
            write_hex_zone_flatbuffers(hex_zone_mapping, temp_path)
            result = read_hex_zone_binary(temp_path)

            assert result == hex_zone_mapping
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
            write_hex_zone_flatbuffers(large_mapping, temp_path)
            result = read_hex_zone_binary(temp_path)

            assert result == large_mapping
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)