from pathlib import Path
from typing import Dict

from flatbuffers import Builder

# local imports
from timezonefinder.flatbuf.HexZoneCollection import HexZoneCollection
from timezonefinder.flatbuf.HexZoneEntry import HexZoneEntry


def get_hex_zone_file_path(data_dir: Path) -> Path:
    """
    Returns the path to the hex_zone file.
    Args:
        data_dir: path to the data directory
    Returns:
        path to the hex_zone file
    """
    return data_dir / "hex_zones.fbs"


def create_hex_zones(
    builder: Builder, mapping: Dict[int, int]
) -> int:
    """
    creates a Flatbuffer representation of the hex_zone mapping.
    Args:
        builder: a flatbuffer builder instance
        mapping: a dict mapping each h3 hexagon id to a unique zone id
    Returns:
        the flatbuffer offset of the hex zone collection
    """
    entry_offsets = []
    # Sorting is important for searching later, though we read into a dict for now.
    for hex_id in sorted(mapping.keys()):
        zone_id = mapping[hex_id]
        HexZoneEntry.Start(builder)
        HexZoneEntry.AddHexId(builder, hex_id)
        HexZoneEntry.AddZoneId(builder, zone_id)
        entry_offset = HexZoneEntry.End(builder)
        entry_offsets.append(entry_offset)

    # Create a vector for the entries
    HexZoneCollection.StartEntriesVector(builder, len(entry_offsets))
    # flatbuffer vectors must be built backwards
    for entry_offset in reversed(entry_offsets):
        builder.PrependUOffsetTRelative(entry_offset)
    entries_vec = builder.EndVector()

    # Create the HexZoneCollection
    HexZoneCollection.Start(builder)
    HexZoneCollection.AddEntries(builder, entries_vec)
    hex_zones_offset = HexZoneCollection.End(builder)

    return hex_zones_offset


def write_hex_zones(output_path: Path, mapping: Dict[int, int]):
    """
    writes the hex_zone mapping to a flatbuffer file.
    Args:
        output_path: the path to the data directory
        mapping: a dict mapping each h3 hexagon id to a unique zone id
    """
    builder = Builder(1024)
    hex_zones_offset = create_hex_zones(builder, mapping)
    builder.Finish(hex_zones_offset)
    buffer = builder.Output()
    file_path = get_hex_zone_file_path(output_path)
    with open(file_path, "wb") as f:
        f.write(buffer)


def read_hex_zones(data_dir: Path) -> HexZoneCollection:
    """
    reads the hex_zone mapping from a flatbuffer file.
    Args:
        data_dir: path to the data directory
    Returns:
        the hex_zone collection, or None if the file does not exist
    """
    file_path = get_hex_zone_file_path(data_dir)
    if not file_path.exists():
        return None
    with open(file_path, "rb") as f:
        buffer = f.read()
    return HexZoneCollection.GetRootAs(buffer)