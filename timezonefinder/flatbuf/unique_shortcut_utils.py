"""
Utility functions for working with unique zone shortcut data in FlatBuffers.
"""

from pathlib import Path
from typing import Dict
import flatbuffers
from timezonefinder.configs import DEFAULT_DATA_DIR
from timezonefinder.flatbuf.UniqueShortcutEntry import (
    UniqueShortcutEntryStart,
    UniqueShortcutEntryEnd,
    UniqueShortcutEntryAddHexId,
    UniqueShortcutEntryAddZoneId,
)
from timezonefinder.flatbuf.UniqueShortcutCollection import (
    UniqueShortcutCollection,
    UniqueShortcutCollectionStart,
    UniqueShortcutCollectionEnd,
    UniqueShortcutCollectionAddEntries,
    UniqueShortcutCollectionStartEntriesVector,
)


def get_unique_shortcut_file_path(output_path: Path = DEFAULT_DATA_DIR) -> Path:
    """Get the path to the unique shortcuts flatbuffer binary file."""
    return output_path / "unique_shortcuts.fbs"


def write_unique_shortcuts_flatbuffers(
    unique_shortcut_mapping: Dict[int, int],
    output_file: Path,
) -> None:
    """
    Write H3 unique zone shortcuts to a FlatBuffer binary file.

    Args:
        unique_shortcut_mapping: Dictionary mapping H3 hexagon IDs to unique zone IDs
        output_file: Path to save the FlatBuffer file

    Returns:
        None
    """
    print(f"writing {len(unique_shortcut_mapping)} unique shortcuts to binary file {output_file}")
    builder = flatbuffers.Builder(0)
    entry_offsets = []

    for hex_id, zone_id in unique_shortcut_mapping.items():
        # Start building shortcut entry
        UniqueShortcutEntryStart(builder)
        UniqueShortcutEntryAddHexId(builder, hex_id)
        UniqueShortcutEntryAddZoneId(builder, zone_id)
        entry_offsets.append(UniqueShortcutEntryEnd(builder))

    # Create vector of shortcut entries
    UniqueShortcutCollectionStartEntriesVector(builder, len(entry_offsets))
    for offset in reversed(entry_offsets):
        builder.PrependUOffsetTRelative(offset)
    entries_vector = builder.EndVector()

    # Create UniqueShortcutCollection
    UniqueShortcutCollectionStart(builder)
    UniqueShortcutCollectionAddEntries(builder, entries_vector)
    collection = UniqueShortcutCollectionEnd(builder)

    builder.Finish(collection)
    buf = builder.Output()

    # Write to file
    with open(output_file, "wb") as f:
        f.write(buf)


def read_unique_shortcuts_binary(
    file_path: Path,
) -> Dict[int, int]:
    """
    Read unique shortcut mapping from a FlatBuffer binary file.

    Args:
        file_path: Path to the unique shortcut FlatBuffer file.

    Returns:
        Dictionary mapping H3 hexagon IDs to zone IDs
    """
    with open(file_path, "rb") as f:
        buf = f.read()

    collection = UniqueShortcutCollection.GetRootAsUniqueShortcutCollection(buf, 0)

    unique_shortcut_mapping = {}
    for i in range(collection.EntriesLength()):
        entry = collection.Entries(i)
        hex_id = entry.HexId()
        zone_id = entry.ZoneId()
        unique_shortcut_mapping[hex_id] = zone_id

    return unique_shortcut_mapping
