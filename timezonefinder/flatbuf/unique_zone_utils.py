"""
Utility functions for working with unique zone data in FlatBuffers.
"""

from pathlib import Path
from typing import Dict
import flatbuffers
from timezonefinder.configs import DEFAULT_DATA_DIR

# a lot of generated functions and classes are in these modules:
import timezonefinder.flatbuf.UniqueZoneEntry as UniqueZoneEntry
import timezonefinder.flatbuf.UniqueZoneCollection as UniqueZoneCollection


def get_unique_zone_file_path(output_path: Path = DEFAULT_DATA_DIR) -> Path:
    """Get the path to the unique zones flatbuffer binary file."""
    return output_path / "shortcuts_unique.fbs"


def write_unique_zones_flatbuffers(
    unique_zone_mapping: Dict[int, int],
    output_file: Path,
) -> None:
    """
    Write unique zone mapping to a FlatBuffer binary file.

    Args:
        unique_zone_mapping: Dictionary mapping H3 hexagon IDs to zone IDs
        output_file: Path to save the FlatBuffer file

    Returns:
        None
    """
    print(f"writing {len(unique_zone_mapping)} unique zone shortcuts to binary file {output_file}")
    builder = flatbuffers.Builder(0)
    entry_offsets = []

    for hex_id, zone_id in unique_zone_mapping.items():
        # Start building unique zone entry
        UniqueZoneEntry.Start(builder)
        UniqueZoneEntry.AddHexId(builder, hex_id)
        UniqueZoneEntry.AddZoneId(builder, zone_id)
        entry_offsets.append(UniqueZoneEntry.End(builder))

    # Create vector of unique zone entries
    UniqueZoneCollection.StartEntriesVector(builder, len(entry_offsets))
    for offset in reversed(entry_offsets):
        builder.PrependUOffsetTRelative(offset)
    entries_vector = builder.EndVector()

    # Create UniqueZoneCollection
    UniqueZoneCollection.Start(builder)
    UniqueZoneCollection.AddEntries(builder, entries_vector)
    collection = UniqueZoneCollection.End(builder)

    builder.Finish(collection)
    buf = builder.Output()

    # Write to file
    with open(output_file, "wb") as f:
        f.write(buf)


def read_unique_zones_binary(
    file_path: Path,
) -> Dict[int, int]:
    """
    Read unique zone mapping from a FlatBuffer binary file.

    Args:
        file_path: Path to the unique zone FlatBuffer file.

    Returns:
        Dictionary mapping H3 hexagon IDs to zone IDs
    """
    with open(file_path, "rb") as f:
        buf = f.read()

    collection = UniqueZoneCollection.UniqueZoneCollection.GetRootAs(buf, 0)

    unique_zone_mapping = {}
    for i in range(collection.EntriesLength()):
        entry = collection.Entries(i)
        hex_id = entry.HexId()
        zone_id = entry.ZoneId()
        unique_zone_mapping[hex_id] = zone_id

    return unique_zone_mapping
