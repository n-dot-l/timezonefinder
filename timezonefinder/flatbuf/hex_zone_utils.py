from pathlib import Path
from typing import Dict

import flatbuffers

from timezonefinder.configs import HEX_ZONES_FILE_NAME
from timezonefinder.flatbuf.HexZoneCollection import (
    HexZoneCollection,
    HexZoneCollectionStart,
    HexZoneCollectionAddEntries,
    HexZoneCollectionStartEntriesVector,
    HexZoneCollectionEnd,
)
from timezonefinder.flatbuf.HexZoneEntry import (
    HexZoneEntry,
    HexZoneEntryStart,
    HexZoneEntryAddH3Id,
    HexZoneEntryAddZoneId,
    HexZoneEntryEnd,
)


def get_hex_zone_file_path(data_dir: Path) -> Path:
    return data_dir / HEX_ZONES_FILE_NAME


def read_hex_zone_data(path: Path) -> Dict[int, int]:
    with open(path, "rb") as f:
        buf = f.read()

    collection = HexZoneCollection.GetRootAs(buf, 0)
    output_dict = {}
    for i in range(collection.EntriesLength()):
        entry = collection.Entries(i)
        h3_id = entry.H3Id()
        zone_id = entry.ZoneId()
        output_dict[h3_id] = zone_id
    return output_dict


def create_hex_zone_data(
    mapping: Dict[int, int], path: Path
) -> None:
    builder = flatbuffers.Builder(1024)
    entry_offsets = []

    for h3_id, zone_id in mapping.items():
        HexZoneEntryStart(builder)
        HexZoneEntryAddH3Id(builder, h3_id)
        HexZoneEntryAddZoneId(builder, zone_id)
        entry_offset = HexZoneEntryEnd(builder)
        entry_offsets.append(entry_offset)

    HexZoneCollectionStartEntriesVector(builder, len(entry_offsets))
    for entry_offset in reversed(entry_offsets):
        builder.PrependUOffsetTRelative(entry_offset)
    entries = builder.EndVector()

    HexZoneCollectionStart(builder)
    HexZoneCollectionAddEntries(builder, entries)
    collection = HexZoneCollectionEnd(builder)
    builder.Finish(collection)

    buf = builder.Output()
    with open(path, "wb") as f:
        f.write(buf)