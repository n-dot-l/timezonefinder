"""
Utility functions for working with unique zone shortcut data in FlatBuffers.
"""

from pathlib import Path
from typing import Dict
import flatbuffers
import numpy as np
from timezonefinder.configs import DEFAULT_DATA_DIR

from timezonefinder.flatbuf.UniqueZoneShortcutEntry import (
    UniqueZoneShortcutEntryStart,
    UniqueZoneShortcutEntryEnd,
    UniqueZoneShortcutEntryAddHexId,
    UniqueZoneShortcutEntryAddZoneId,
)
from timezonefinder.flatbuf.UniqueZoneShortcutCollection import (
    UniqueZoneShortcutCollection,
    UniqueZoneShortcutCollectionStart,
    UniqueZoneShortcutCollectionEnd,
    UniqueZoneShortcutCollectionAddEntries,
    UniqueZoneShortcutCollectionStartEntriesVector,
)


def get_unique_zone_shortcut_file_path(output_path: Path = DEFAULT_DATA_DIR) -> Path:
    """Get the path to the unique zone shortcuts flatbuffer binary file."""
    return output_path / "unique_zone_shortcuts.fbs"


def write_unique_zone_shortcuts_flatbuffers(
    unique_zone_mapping: Dict[int, int],
    output_file: Path = DEFAULT_DATA_DIR,
) -> None:
    """
    Write unique zone shortcuts to a FlatBuffer binary file.

    Args:
        unique_zone_mapping: Dictionary mapping H3 hexagon IDs to unique zone IDs
        output_file: Path to save the FlatBuffer file

    Returns:
        None
    """
    print(f"writing {len(unique_zone_mapping)} unique zone shortcuts to binary file {output_file}")
    builder = flatbuffers.Builder(0)
    entry_offsets = []

    for hex_id, zone_id in unique_zone_mapping.items():
        # Start building unique zone shortcut entry
        UniqueZoneShortcutEntryStart(builder)
        UniqueZoneShortcutEntryAddHexId(builder, hex_id)
        UniqueZoneShortcutEntryAddZoneId(builder, zone_id)
        entry_offsets.append(UniqueZoneShortcutEntryEnd(builder))

    # Create vector of shortcut entries
    UniqueZoneShortcutCollectionStartEntriesVector(builder, len(entry_offsets))
    for offset in reversed(entry_offsets):
        builder.PrependUOffsetTRelative(offset)
    collection = UniqueZoneShortcutCollectionEnd(builder)

    builder.Finish(collection)
    buf = builder.Output()

    # Write to file
    with open(output_file, "wb") as f:
        f.write(buf)


def read_unique_zone_shortcuts_binary(
    file_path: Path,
) -> Dict[int, int]:
    """
    Read unique zone shortcut mapping from a FlatBuffer binary file.

    Args:
        file_path: Path to the unique zone shortcut FlatBuffer file.

    Returns:
        Dictionary mapping H3 hexagon IDs to unique zone IDs
    """
    with open(file_path, "rb") as f:
        buf = f.read()

    collection = UniqueZoneShortcutCollection.GetRootAsUniqueZoneShortcutCollection(buf, 0)

    unique_zone_mapping = {}
    for i in range(collection.EntriesLength()):
        entry = collection.Entries(i)
        hex_id = entry.HexId()
        zone_id = entry.ZoneId()
        unique_zone_mapping[hex_id] = zone_id

    return unique_zone_mapping