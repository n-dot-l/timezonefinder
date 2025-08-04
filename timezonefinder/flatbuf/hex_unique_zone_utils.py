```python
"""
Utility functions for working with unique zone data in FlatBuffers.
"""

from pathlib import Path
from typing import Dict
import flatbuffers
from timezonefinder.configs import DEFAULT_DATA_DIR
from timezonefinder.flatbuf.HexUniqueZoneEntry import (
    HexUniqueZoneEntryStart,
    HexUniqueZoneEntryEnd,
    HexUniqueZoneEntryAddHexId,
    HexUniqueZoneEntryAddZoneId,
)
from timezonefinder.flatbuf.HexUniqueZoneCollection import (
    HexUniqueZoneCollection,
    HexUniqueZoneCollectionStart,
    HexUniqueZoneCollectionEnd,
    HexUniqueZoneCollectionAddEntries,
    HexUniqueZoneCollectionStartEntriesVector,
)


def get_unique_zone_file_path(output_path: Path = DEFAULT_DATA_DIR) -> Path:
    """Get the path to the unique_zone flatbuffer binary file."""
    return output_path / "unique_zone.fbs"


def write_unique_zone_flatbuffers(
    unique_zone_mapping: Dict[int, int],
    output_file: Path,
) -> None:
    """
    Write H3 unique zones to a FlatBuffer binary file.

    Args:
        unique_zone_mapping: Dictionary mapping H3 hexagon IDs to unique zone ID
        output_file: Path to save the FlatBuffer file

    Returns:
        None
    """
    print(f"writing {len(unique_zone_mapping)} unique zone shortcuts to binary file {output_file}")
    builder = flatbuffers.Builder(0)
    entry_offsets = []

    for hex_id, zone_id in unique_zone_mapping.items():
        # Start building unique zone entry
        HexUniqueZoneEntryStart(builder)
        HexUniqueZoneEntryAddHexId(builder, hex_id)
        HexUniqueZoneEntryAddZoneId(builder, zone_id)
        entry_offsets.append(HexUniqueZoneEntryEnd(builder))

    # Create vector of unique zone entries
    HexUniqueZoneCollectionStartEntriesVector(builder, len(entry_offsets))
    for offset in reversed(entry_offsets):
        builder.PrependUOffsetTRelative(offset)
    entries_vector = builder.EndVector()

    # Create HexUniqueZoneCollection
    HexUniqueZoneCollectionStart(builder)
    HexUniqueZoneCollectionAddEntries(builder, entries_vector)
    collection = HexUniqueZoneCollectionEnd(builder)

    builder.Finish(collection)
    buf = builder.Output()

    # Write to file
    with open(output_file, "wb") as f:
        f.write(buf)


def read_unique_zone_binary(
    file_path: Path,
) -> Dict[int, int]:
    """
    Read unique zone mapping from a FlatBuffer binary file.

    Args:
        file_path: Path to the unique zone FlatBuffer file.

    Returns:
        Dictionary mapping H3 hexagon IDs to unique zone IDs
    """
    with open(file_path, "rb") as f:
        buf = f.read()

    collection = HexUniqueZoneCollection.GetRootAsHexUniqueZoneCollection(buf, 0)

    unique_zone_mapping = {}
    for i in range(collection.EntriesLength()):
        entry = collection.Entries(i)
        hex_id = entry.HexId()
        zone_id = entry.ZoneId()
        unique_zone_mapping[hex_id] = zone_id

    return unique_zone_mapping