import bisect
import mmap
from pathlib import Path
from typing import Dict, List, Optional

import flatbuffers

from timezonefinder.flatbuf.HexZoneCollection import HexZoneCollection
from timezonefinder.flatbuf.HexZoneEntry import HexZoneEntry

# just for typing hints:
HexZoneEntries = List[HexZoneEntry]


def get_hex_zone_file_path(path: Path) -> Path:
    return path / "hex_zones.fbs"


def write_hex_zones_flatbuffer(hex_zones: Dict[int, int], output_path: Path):
    """writes the hex-zone mapping to a flatbuffer file"""
    builder = flatbuffers.Builder(1024)
    entries = []

    # Sort by hex_id for efficient searching (e.g., binary search)
    sorted_hex_ids = sorted(hex_zones.keys())

    for hex_id in sorted_hex_ids:
        zone_id = hex_zones[hex_id]
        HexZoneEntry.Start(builder)
        HexZoneEntry.AddHexId(builder, hex_id)
        HexZoneEntry.AddZoneId(builder, zone_id)
        entry = HexZoneEntry.End(builder)
        entries.append(entry)

    HexZoneCollection.StartEntriesVector(builder, len(entries))
    # Add entries in reverse order to the buffer
    for entry in reversed(entries):
        builder.PrependUOffsetTRelative(entry)
    entries_vector = builder.EndVector()

    HexZoneCollection.Start(builder)
    HexZoneCollection.AddEntries(builder, entries_vector)
    collection = HexZoneCollection.End(builder)

    builder.Finish(collection)
    buf = builder.Output()

    with open(output_path, "wb") as f:
        f.write(buf)


class HexZoneManager:
    __slots__ = (
        "file_path",
        "in_memory",
        "_hex_zones",
        "_hex_zone_ids",
        "_file",
        "_buffer",
    )

    def __init__(self, data_path: Path, in_memory: bool = False):
        self.file_path = get_hex_zone_file_path(data_path)
        if not self.file_path.exists():
            raise FileNotFoundError(f"required data file not found: {self.file_path}")

        self.in_memory = in_memory
        self._hex_zones: Optional[HexZoneEntries] = None
        self._hex_zone_ids: Optional[List[int]] = None

        if self.in_memory:
            with open(self.file_path, "rb") as f:
                self._buffer = f.read()
            self._hex_zones = self._read_hex_zones()
            self._hex_zone_ids = [entry.HexId() for entry in self._hex_zones]
            self._file = None
        else:
            self._file = open(self.file_path, "rb")
            self._buffer = mmap.mmap(self._file.fileno(), 0, access=mmap.ACCESS_READ)
            # only read the hex ids in advance for searching
            hex_zones = self._read_hex_zones()
            self._hex_zone_ids = [entry.HexId() for entry in hex_zones]

    def __del__(self):
        if hasattr(self, "_file") and self._file is not None:
            self._file.close()

    def _read_hex_zones(self) -> HexZoneEntries:
        collection = HexZoneCollection.GetRootAs(self._buffer, 0)
        return [collection.Entries(j) for j in range(collection.EntriesLength())]

    def get_zone_id(self, hex_id: int) -> Optional[int]:
        # find the index of the hex_id in the sorted list of hex_ids
        # cf. https://docs.python.org/3/library/bisect.html
        if self._hex_zone_ids is None:
            return None
        idx = bisect.bisect_left(self._hex_zone_ids, hex_id)

        if idx == len(self._hex_zone_ids) or self._hex_zone_ids[idx] != hex_id:
            # hex_id not found
            return None

        if self.in_memory:
            # list of entries is completely in memory
            entry = self._hex_zones[idx]
        else:
            # read the entry from the file
            collection = HexZoneCollection.GetRootAs(self._buffer, 0)
            entry = collection.Entries(idx)

        return entry.ZoneId()