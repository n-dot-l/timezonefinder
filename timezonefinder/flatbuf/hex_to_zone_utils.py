"""
Utility functions for working with hex_to_zone data in FlatBuffers.
"""
from pathlib import Path
from typing import Dict
import flatbuffers
from timezonefinder.configs import DEFAULT_DATA_DIR
from timezonefinder.flatbuf.HexToZoneEntry import (
    HexToZoneEntryStart,
    HexToZoneEntryEnd,
    HexToZoneEntryAddHexId,
    HexToZoneEntryAddZoneId,
)
from timezonefinder.flatbuf.HexToZoneCollection import (
    HexToZoneCollection,
    HexToZoneCollectionStart,
    HexToZoneCollectionEnd,
    HexToZoneCollectionAddEntries,
    HexToZoneCollectionStartEntriesVector,
)


def get_hex_to_zone_file_path(output_path: Path = DEFAULT_DATA_DIR) -> Path:
    """Get the path to the hex_to_zone flatbuffer binary file."""
    return output_path / "hex_to_zone.fbs"


def write_hex_to_zone_flatbuffers(
    hex_to_zone_mapping: Dict[int, int],
    output_file: Path = DEFAULT_DATA_DIR,
) -> None:
    """
    Write H3 hex_to_zone to a FlatBuffer binary file.

    Args:
        hex_to_zone_mapping: Dictionary mapping H3 hexagon IDs to unique zone ID
        output_file: Path to save the FlatBuffer file

    Returns:
        None
    """
    print(f"writing {len(hex_to_zone_mapping)} hex_to_zone entries to binary file {output_file}")
    builder = flatbuffers.Builder(0)
    entry_offsets = []

    for hex_id, zone_id in hex_to_zone_mapping.items():
        # Start building shortcut entry
        HexToZoneEntryStart(builder)
        HexToZoneEntryAddHexId(builder, hex_id)
        HexToZoneEntryAddZoneId(builder, zone_id)
        entry_offsets.append(HexToZoneEntryEnd(builder))

    # Create vector of shortcut entries
    HexToZoneCollectionStartEntriesVector(builder, len(entry_offsets))
    for offset in reversed(entry_offsets):
        builder.PrependUOffsetTRelative(offset)
    entries_vector = builder.EndVector()

    # Create HexToZoneCollection
    HexToZoneCollectionStart(builder)
    HexToZoneCollectionAddEntries(builder, entries_vector)
    collection = HexToZoneCollectionEnd(builder)

    builder.Finish(collection)
    buf = builder.Output()

    # Write to file
    with open(output_file, "wb") as f:
        f.write(buf)


def read_hex_to_zone_binary(
    file_path: Path,
) -> Dict[int, int]:
    """
    Read hex_to_zone mapping from a FlatBuffer binary file.

    Args:
        file_path: Path to the hex_to_zone FlatBuffer file.

    Returns:
        Dictionary mapping H3 hexagon IDs to zone IDs
    """
    with open(file_path, "rb") as f:
        buf = f.read()

    collection = HexToZoneCollection.GetRootAsHexToZoneCollection(buf, 0)

    hex_to_zone_mapping = {}
    for i in range(collection.EntriesLength()):
        entry = collection.Entries(i)
        hex_id = entry.HexId()
        zone_id = entry.ZoneId()
        hex_to_zone_mapping[hex_id] = zone_id

    return hex_to_zone_mapping
