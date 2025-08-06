from typing import Dict, List, Optional, Tuple, Union
from pathlib import Path

import flatbuffers
import numpy as np

from timezonefinder.flatbuf.HexShortcutCollection import HexShortcutCollection
from timezonefinder.flatbuf.HexShortcutEntry import (
    End,
    HexShortcutEntryAddHexId,
    HexShortcutEntryAddZoneId,
    HexShortcutEntryStart,
)
from timezonefinder.flatbuf.HexShortcutCollection import (
    AddEntries,
    HexShortcutCollectionEnd,
    HexShortcutCollectionStart,
    HexShortcutCollectionStartEntriesVector,
)

# must be the same as in the schema
# HexShortcutEntry: ulong, short -> 8 + 2 = 10 bytes. but flatbuffers has padding and vtable. so size is not fixed.
# with ~450k entries, we need about 5MB
BUFFER_SIZE = 6_000_000
HEX_SHORTCUT_FILENAME = "hex_shortcuts.fbs"


def get_hex_shortcut_file_path(path: Union[str, Path]) -> str:
    """
    Constructs the full path to the hex shortcut file.
    :param path: the path to the data directory
    :return: the full path to the hex shortcut file
    """
    return str(Path(path) / HEX_SHORTCUT_FILENAME)


def read_hex_shortcuts(path: str) -> Optional[np.ndarray]:
    """
    reads the mapping from hex_id to zone_id from a flatbuffer file
    and returns a numpy array for fast lookups.
    The first row contains the hex_ids, the second row contains the zone_ids.
    The array is sorted by hex_id.
    """
    try:
        with open(path, "rb") as fh:
            buf = fh.read()
    except FileNotFoundError:
        return None

    coll = HexShortcutCollection.GetRootAs(buf, 0)
    n = coll.EntriesLength()
    # Note: flatbuffers stores uint64 as python int which is fine for numpy uint64
    hex_ids = np.empty(shape=n, dtype=np.uint64)
    zone_ids = np.empty(shape=n, dtype=np.int16)
    for i in range(n):
        entry = coll.Entries(i)
        hex_ids[i] = entry.HexId()
        zone_ids[i] = entry.ZoneId()

    return np.array([hex_ids, zone_ids])


def create_hex_shortcuts(path: str, shortcuts: Dict[int, int]):
    """
    writes the mapping from hex_id to zone_id to a flatbuffer file
    :param path: path to the flatbuffer file
    :param shortcuts: a mapping from hex_id to zone_id
    """
    # sort the shortcuts by hex_id to allow for binary search
    sorted_shortcuts: List[Tuple[int, int]] = sorted(shortcuts.items())

    builder = flatbuffers.Builder(BUFFER_SIZE)
    write_hex_shortcuts_to_buffer(builder, sorted_shortcuts)
    buf = builder.Output()

    # increase the buffer size if the created buffer is too small
    # flatbuffers.Builder grows the buffer automatically, but the python implementation has a bug and does not give
    # access to the new buffer size.
    # see: https://github.com/google/flatbuffers/issues/6335
    if len(buf) > BUFFER_SIZE:
        # NOTE: this is a workaround. we are creating the buffer twice.
        builder = flatbuffers.Builder(len(buf))
        write_hex_shortcuts_to_buffer(builder, sorted_shortcuts)
        buf = builder.Output()

    with open(path, "wb") as fh:
        fh.write(buf)


def write_hex_shortcuts_to_buffer(builder, sorted_shortcuts: List[Tuple[int, int]]):
    n = len(sorted_shortcuts)
    offsets = np.empty(shape=n, dtype=np.uint32)

    for i, (hex_id, zone_id) in enumerate(sorted_shortcuts):
        HexShortcutEntryStart(builder)
        # Note: h3 ids are uint64, which is handled correctly by the python flatbuffers lib
        HexShortcutEntryAddHexId(builder, hex_id)
        HexShortcutEntryAddZoneId(builder, zone_id)
        offsets[n - 1 - i] = End(builder)

    HexShortcutCollectionStartEntriesVector(builder, n)
    # push the offsets in reverse order
    for offset in offsets:
        builder.PrependUOffsetRelative(offset)
    entries = builder.EndVector()

    HexShortcutCollectionStart(builder)
    AddEntries(builder, entries)
    coll = HexShortcutCollectionEnd(builder)
    builder.Finish(coll)
