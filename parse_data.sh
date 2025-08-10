#!/bin/bash

WORKING_FOLDER_NAME=tmp
ARCHIVE_NAME=data_downloaded.zip
ZIP_ARCHIVE_PATH=./$WORKING_FOLDER_NAME/$ARCHIVE_NAME
JSON_PREFIX=combined
JSON_SUFFIX=.json
DESTINATION_PATH=./timezonefinder
URL_PREFIX=https://github.com/evansiroky/timezone-boundary-builder/releases/latest/download/timezones
URL_SUFFIX=.geojson.zip

echo "TIME ZONE DATA PARSING SCRIPT"

# make script work independent of where you invoke it from
parent_path=$(
    cd "$(dirname "${BASH_SOURCE[0]}")" || exit 1
    pwd -P
)
cd "$parent_path" || exit 1
mkdir -p "$WORKING_FOLDER_NAME" # if does not exist

echo "use timezone data with oceans (0: No, 1: Yes)? "
read -r WITH_OCEANS
if [ "$WITH_OCEANS" -eq 1 ]; then
    INTERFIX=-with-oceans
else
    INTERFIX=""
fi
JSON_FILE_NAME=$JSON_PREFIX$INTERFIX$JSON_SUFFIX
JSON_PATH=./$WORKING_FOLDER_NAME/$JSON_FILE_NAME

if [ -f $JSON_PATH ]; then
    echo "skip unpacking: $JSON_PATH already exists."
else
    if [ -f $ZIP_ARCHIVE_PATH ]; then
        echo "skipping download: $ZIP_ARCHIVE_PATH already exists."
    else
        URL=$URL_PREFIX$INTERFIX$URL_SUFFIX
        echo "DOWNLOADING $URL"

        # install command mac:
        # brew install wget
        wget -O $ZIP_ARCHIVE_PATH $URL --tries=3
    fi
    echo "UNPACKING..."
    unzip $ZIP_ARCHIVE_PATH -d $WORKING_FOLDER_NAME
fi

echo "START PARSING..."
SCRIPT_PATH=./scripts/file_converter.py
echo "calling $SCRIPT_PATH:"
python "$SCRIPT_PATH" -inp "$JSON_PATH" -out "$DESTINATION_PATH"

echo "creating unique zone shortcuts and pruning shortcut file..."
python -c "
import numpy as np
from timezonefinder.flatbuf.shortcut_utils import (
    get_shortcut_file_path,
    read_shortcuts_binary,
    write_shortcuts_flatbuffers,
)
from timezonefinder.flatbuf.unique_zone_utils import (
    get_unique_zone_file_path,
    write_unique_zones_flatbuffers,
)
from timezonefinder.np_binary_helpers import (
    get_zone_ids_path,
    read_per_polygon_vector,
)
from scripts.configs import BINARY_FILE_DIR

print('creating unique zone mapping...')

# load existing data
shortcut_path = get_shortcut_file_path(BINARY_FILE_DIR)
shortcut_mapping = read_shortcuts_binary(shortcut_path)

zone_ids_path = get_zone_ids_path(BINARY_FILE_DIR)
zone_ids = read_per_polygon_vector(zone_ids_path)

# compute unique zone mapping
unique_zone_mapping = {}
for hex_id, poly_ids in shortcut_mapping.items():
    if len(poly_ids) == 0:
        continue
    p_zone_ids = zone_ids[poly_ids]
    unique_ids = np.unique(p_zone_ids)

    if len(unique_ids) == 1:
        unique_zone_mapping[hex_id] = int(unique_ids[0])

# write new mapping to file
output_path = get_unique_zone_file_path(BINARY_FILE_DIR)
write_unique_zones_flatbuffers(unique_zone_mapping, output_path)

print(f'unique zone mapping with {len(unique_zone_mapping)} entries has been created.')

# prune shortcut mapping
print('pruning shortcut mapping...')
for hex_id in unique_zone_mapping:
    if hex_id in shortcut_mapping:
        shortcut_mapping[hex_id] = []

write_shortcuts_flatbuffers(shortcut_mapping, shortcut_path)
print('shortcut mapping has been pruned.')
"

echo "runnings tests..."
if ! tox; then
    # assert that all tests are passing
    echo "tests failed!"
    exit 1
fi

# minor version bump
uv run --bump minor

# TODO
 read -r -p "should all temporary data files be deleted (0: No, 1: Yes)?" do_deletion
 if [ "$do_deletion" -eq 1 ]; then
    rm -r "$WORKING_FOLDER_NAME"
fi

# TODO add changelog entry: keep title, current date, parse data version
# $(uv version) (2022-12-06)
#------------------
#
#* updated the data to `2022g <https://github.com/evansiroky/timezone-boundary-builder/releases/tag/2022g>`__.
#echo -e "DATA-Line-1\n$(cat input)" > input

echo "SUCCESS! the new package version $(uv version) can now be released!"
