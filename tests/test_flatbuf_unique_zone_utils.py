from pathlib import Path
from typing import Dict
import pytest
from timezonefinder.flatbuf.unique_zone_utils import (
    get_unique_zone_file_path,
    read_unique_zones_binary,
    write_unique_zones_flatbuffers,
)

# Sample data for testing
SAMPLE_UNIQUE_ZONE_MAPPING: Dict[int, int] = {
    12345: 1,
    67890: 5,
    99999: 10,
}


@pytest.fixture
def unique_zone_file(tmp_path: Path) -> Path:
    """Create a temporary unique zone file for testing."""
    return get_unique_zone_file_path(tmp_path)


def test_write_read_unique_zones_flatbuffers(
    unique_zone_file: Path,
):
    """Test writing and reading unique zone data using FlatBuffers."""
    write_unique_zones_flatbuffers(SAMPLE_UNIQUE_ZONE_MAPPING, unique_zone_file)
    assert unique_zone_file.exists()

    # Read data back
    read_mapping = read_unique_zones_binary(unique_zone_file)

    # Validate the read data
    assert len(read_mapping) == len(SAMPLE_UNIQUE_ZONE_MAPPING)
    for hex_id, zone_id in SAMPLE_UNIQUE_ZONE_MAPPING.items():
        assert hex_id in read_mapping
        assert read_mapping[hex_id] == zone_id


def test_read_real_data_non_existent():
    """Test reading a non-existent unique zone data file."""
    # This test requires the data file not to be present
    unique_zone_file = get_unique_zone_file_path(Path("non_existent_dir"))
    with pytest.raises(FileNotFoundError):
        read_unique_zones_binary(unique_zone_file)


def test_empty_mapping(unique_zone_file: Path):
    """Test writing and reading an empty mapping."""
    write_unique_zones_flatbuffers({}, unique_zone_file)
    assert unique_zone_file.exists()
    read_mapping = read_unique_zones_binary(unique_zone_file)
    assert len(read_mapping) == 0


def test_large_mapping(unique_zone_file: Path):
    """Test with a larger number of entries."""
    large_mapping = {i: i % 100 for i in range(1000)}
    write_unique_zones_flatbuffers(large_mapping, unique_zone_file)
    read_mapping = read_unique_zones_binary(unique_zone_file)
    assert len(read_mapping) == 1000
    assert read_mapping[999] == 99
