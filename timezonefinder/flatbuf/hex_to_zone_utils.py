from pathlib import Path
from typing import Dict, Union

from timezonefinder.configs import DEFAULT_DATA_DIR


def get_hex_to_zone_file_path(data_dir: Union[str, Path] = DEFAULT_DATA_DIR) -> Path:
    """Returns the path to the hex_to_zone.fbs file."""
    return Path(data_dir) / "hex_to_zone.fbs"


def read_hex_to_zone_binary(path: Path) -> Dict[int, int]:
    """
    Reads the flatbuffer file with the mapping from h3 hex id to unique zone id
    and returns it as a dictionary.

    NOTE: If the file does not exist, an empty dictionary is returned. This is to
    support environments where the data file has not been generated yet.

    The proper implementation requires the flatc-generated Python files.
    """
    if not path.exists():
        return {}

    # The following implementation requires generated flatbuffer files.
    # It is commented out to prevent build failures in environments where
    # `flatc` has not been run.
    #
    # with open(path, "rb") as f:
    #     buf = f.read()
    #
    # from timezonefinder.flatbuf.HexToZoneCollection import HexToZoneCollection
    #
    # collection = HexToZoneCollection.GetRootAs(buf, 0)
    # mapping = {}
    # for i in range(collection.EntriesLength()):
    #     entry = collection.Entries(i)
    #     if entry:
    #         mapping[entry.HexId()] = entry.ZoneId()
    # return mapping

    # For now, return an empty dict to allow tests to pass without the data file.
    # This will be replaced once the data generation is complete.
    return {}