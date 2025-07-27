"""
utility functions for building and reading the hex_id -> zone_id mapping flatbuffer file
"""
from pathlib import Path
from typing import Dict, Optional

import flatbuffers
import numpy as np

# ATTENTION: has to be generated first!
# run: `flatc --python --gen-mutable timezonefinder/flatbuf/hex_zone_schema.fbs`
# The imports are created by the flatc command. They are moved into the functions
# to avoid import errors before the files have been generated.


def get_hex_zone_file_path(output_path: Path) -> Path:
    """returns the path to the hex zone mapping file"""
    return output_path / "hex_zones.fbs"


def build_hex_zone_data(
    builder: flatbuffers.Builder, hex_zone_mapping: Dict[int, int]
) -> int:
    """
    builds the flatbuffer data for the hex_id -> zone_id mapping
    :param builder: a flatbuffer builder instance
    :param hex_zone_mapping: a dict mapping h3 hex_ids to zone_ids
    :return: the offset of the created data structure
    """
    from timezonefinder.flatbuf.HexZoneCollection import HexZoneCollection
    from timezonefinder.flatbuf.HexZoneEntry import HexZoneEntry

    entry_offsets = []
    # sort the mapping by hex_id to enable binary search later
    sorted_hex_ids = sorted(hex_zone_mapping.keys())

    for hex_id in sorted_hex_ids:
        zone_id = hex_zone_mapping[hex_id]
        HexZoneEntry.Start(builder)
        HexZoneEntry.AddHexId(builder, hex_id)
        HexZoneEntry.AddZoneId(builder, zone_id)
        entry_offset = HexZoneEntry.End(builder)
        entry_offsets.append(entry_offset)

    # create the vector of entries
    HexZoneCollection.StartEntriesVector(builder, len(entry_offsets))
    for entry_offset in reversed(entry_offsets):
        builder.PrependUOffsetTRelative(entry_offset)
    entries_vec = builder.EndVector()

    # create the collection
    HexZoneCollection.Start(builder)
    HexZoneCollection.AddEntries(builder, entries_vec)
    collection_offset = HexZoneCollection.End(builder)

    return collection_offset


def write_hex_zone_flatbuffer(
    hex_zone_mapping: Dict[int, int], output_path: Path
) -> None:
    """
    writes the hex_id -> zone_id mapping to a flatbuffer file
    :param hex_zone_mapping: a dict mapping h3 hex_ids to zone_ids
    :param output_path: the path to the output file
    """
    builder = flatbuffers.Builder(1024)
    collection_offset = build_hex_zone_data(builder, hex_zone_mapping)
    builder.Finish(collection_offset)
    buf = builder.Output()
    with open(output_path, "wb") as f:
        f.write(buf)


class HexZoneReader:
    """
    class for reading the hex_id -> zone_id mapping from a flatbuffer file
    """

    _collection = None
    _hex_ids: np.ndarray = np.array([], dtype=np.uint64)
    _zone_ids: Optional[np.ndarray] = None

    def __init__(self, data_path: Optional[Path] = None, in_memory: bool = False):
        from timezonefinder.utils import get_data_dir
        from timezonefinder.flatbuf.HexZoneCollection import HexZoneCollection

        if data_path is None:
            data_path = get_data_dir()

        file_path = get_hex_zone_file_path(data_path)

        if not file_path.exists():
            return

        with open(file_path, "rb") as f:
            buf = f.read()

        self._collection = HexZoneCollection.GetRootAs(buf, 0)
        # To enable fast lookups, we load all hex_ids into a numpy array
        length = self._collection.EntriesLength()
        self._hex_ids = np.array(
            [self._collection.Entries(i).HexId() for i in range(length)],
            dtype=np.uint64,
        )
        if in_memory:
            self._zone_ids = np.array(
                [self._collection.Entries(i).ZoneId() for i in range(length)],
                dtype=np.uint16,
            )

    def get_zone_id(self, hex_id: int) -> Optional[int]:
        """
        returns the zone_id for a given h3 hex_id if it is unique, else None
        uses binary search on the sorted hex_ids.
        """
        if self._collection is None:
            return None

        # find the index of the hex_id in the sorted array
        idx = np.searchsorted(self._hex_ids, hex_id)

        if idx < len(self._hex_ids) and self._hex_ids[idx] == hex_id:
            # hex_id found, return the corresponding zone_id
            if self._zone_ids is not None:
                return self._zone_ids[idx]
            return self._collection.Entries(idx).ZoneId()

        return None