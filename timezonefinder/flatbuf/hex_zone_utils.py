"""
Utility functions for working with the hex_id->zone_id mapping data in FlatBuffers.
"""
from pathlib import Path
from typing import Dict
import flatbuffers
from timezonefinder.configs import DEFAULT_DATA_DIR

# These imports will fail until flatc is run on the new schema
# I am assuming the generated names based on the schema and flatc conventions.
from timezonefinder.flatbuf.HexZoneEntry import (
    HexZoneEntryStart,
    HexZoneEntryEnd,
    HexZoneEntryAddHexId,
    HexZoneEntryAddZoneId,
)
from timezonefinder.flatbuf.HexZoneCollection import (
    HexZoneCollection,
    HexZoneCollectionStart,
    HexZoneCollectionEnd,
    HexZoneCollectionAddEntries,
    HexZoneCollectionStartEntriesVector,
)


def get_hex_zone_file_path(output_path: Path = DEFAULT_DATA_DIR) -> Path:
    """Get the path to the hex_to_zone flatbuffer binary file."""
    return output_path / "hex_to_zone.fbs"


def write_hex_zone_flatbuffers(
    hex_zone_mapping: Dict[int, int],
    output_file: Path,
) -> None:
    """
    Write H3 hexagon to unique zone ID mapping to a FlatBuffer binary file.

    Args:
        hex_zone_mapping: Dictionary mapping H3 hexagon IDs to unique zone IDs
        output_file: Path to save the FlatBuffer file

    Returns:
        None
    """
    print(f"writing {len(hex_zone_mapping)} hex->zone entries to binary file {output_file}")
    builder = flatbuffers.Builder(0)
    entry_offsets = []

    # Sort items for deterministic output
    for hex_id, zone_id in sorted(hex_zone_mapping.items()):
        # Start building hex zone entry
        HexZoneEntryStart(builder)
        HexZoneEntryAddHexId(builder, hex_id)
        HexZoneEntryAddZoneId(builder, zone_id)
        entry_offsets.append(HexZoneEntryEnd(builder))

    # Create vector of shortcut entries
    HexZoneCollectionStartEntriesVector(builder, len(entry_offsets))
    for offset in reversed(entry_offsets):
        builder.PrependUOffsetTRelative(offset)
    entries_vector = builder.EndVector()

    # Create HexZoneCollection
    HexZoneCollectionStart(builder)
    HexZoneCollectionAddEntries(builder, entries_vector)
    collection = HexZoneCollectionEnd(builder)

    builder.Finish(collection)
    buf = builder.Output()

    # Write to file
    with open(output_file, "wb") as f:
        f.write(buf)


def read_hex_zone_binary(
    file_path: Path,
) -> Dict[int, int]:
    """
    Read hex->zone mapping from a FlatBuffer binary file.

    Args:
        file_path: Path to the hex_to_zone FlatBuffer file.

    Returns:
        Dictionary mapping H3 hexagon IDs to unique zone IDs
    """
    try:
        with open(file_path, "rb") as f:
            buf = f.read()
    except FileNotFoundError:
        # It's possible the file doesn't exist if no unique zones were found
        # or if using older data. Return an empty dict.
        return {}

    collection = HexZoneCollection.GetRootAs(buf, 0)

    hex_zone_mapping = {}
    for i in range(collection.EntriesLength()):
        entry = collection.Entries(i)
        hex_id = entry.HexId()
        zone_id = entry.ZoneId()
        hex_zone_mapping[hex_id] = zone_id

    return hex_zone_mapping
