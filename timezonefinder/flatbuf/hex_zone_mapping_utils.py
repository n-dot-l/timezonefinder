"""
Utility functions for working with the hex_id to unique zone_id mapping in FlatBuffers.
"""
from pathlib import Path
from typing import Dict
import flatbuffers

from timezonefinder.configs import DEFAULT_DATA_DIR
from timezonefinder.flatbuf.HexZoneMappingEntry import (
    HexZoneMappingEntryStart,
    HexZoneMappingEntryEnd,
    HexZoneMappingEntryAddHexId,
    HexZoneMappingEntryAddZoneId,
)
from timezonefinder.flatbuf.HexZoneMappingCollection import (
    HexZoneMappingCollection,
    HexZoneMappingCollectionStart,
    HexZoneMappingCollectionEnd,
    HexZoneMappingCollectionAddEntries,
    HexZoneMappingCollectionStartEntriesVector,
)


def get_hex_zone_mapping_file_path(output_path: Path = DEFAULT_DATA_DIR) -> Path:
    """Get the path to the hex zone mapping flatbuffer binary file."""
    return output_path / "hex_zone_mapping.fbs"


def write_hex_zone_mapping_flatbuffers(
    hex_zone_mapping: Dict[int, int],
    output_file: Path,
) -> None:
    """
    Write H3 hex_id to unique zone_id mapping to a FlatBuffer binary file.

    Args:
        hex_zone_mapping: Dictionary mapping H3 hexagon IDs to unique zone IDs
        output_file: Path to save the FlatBuffer file

    Returns:
        None
    """
    print(f"writing {len(hex_zone_mapping)} hex to unique zone mappings to binary file {output_file}")
    builder = flatbuffers.Builder(0)
    entry_offsets = []

    for hex_id, zone_id in hex_zone_mapping.items():
        # Start building shortcut entry
        HexZoneMappingEntryStart(builder)
        HexZoneMappingEntryAddHexId(builder, hex_id)
        HexZoneMappingEntryAddZoneId(builder, zone_id)
        entry_offsets.append(HexZoneMappingEntryEnd(builder))

    # Create vector of shortcut entries
    HexZoneMappingCollectionStartEntriesVector(builder, len(entry_offsets))
    for offset in reversed(entry_offsets):
        builder.PrependUOffsetTRelative(offset)
    entries_vector = builder.EndVector()

    # Create ShortcutCollection
    HexZoneMappingCollectionStart(builder)
    HexZoneMappingCollectionAddEntries(builder, entries_vector)
    collection = HexZoneMappingCollectionEnd(builder)

    builder.Finish(collection)
    buf = builder.Output()

    # Write to file
    with open(output_file, "wb") as f:
        f.write(buf)


def read_hex_zone_mapping_binary(
    file_path: Path,
) -> Dict[int, int]:
    """
    Read hex to zone_id mapping from a FlatBuffer binary file.

    Args:
        file_path: Path to the hex zone mapping FlatBuffer file.

    Returns:
        Dictionary mapping H3 hexagon IDs to unique zone IDs
    """
    with open(file_path, "rb") as f:
        buf = f.read()

    collection = HexZoneMappingCollection.GetRootAs(buf, 0)

    hex_zone_mapping = {}
    for i in range(collection.EntriesLength()):
        entry = collection.Entries(i)
        hex_id = entry.HexId()
        zone_id = entry.ZoneId()
        hex_zone_mapping[hex_id] = zone_id

    return hex_zone_mapping