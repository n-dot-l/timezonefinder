#  Copyright (c) 2014-2024 Jannik Michelfeuer
#
#  This file is part of timezonefinder.
#
#  timezonefinder is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Lesser General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  timezonefinder is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public License
#  along with timezonefinder.  If not, see <http://www.gnu.org/licenses/>.
import warnings
from typing import Dict, List, Optional, Union

import h3
import numpy as np

from ._numba_replacements import njit_if_numba
from .configs import H3_RESOLUTION
from .coord_accessors import get_coords_for_poly
from .flatbuf.polygon_utils import read_polygon_data
from .flatbuf.shortcut_utils import get_shortcut_file_path, read_shortcut_data
from .inside_poly_extension.inside_polygon_int import (
    pt_in_poly_int,
    pt_in_poly_int_with_hole,
)
from .utils import (
    get_data_dir,
    get_in_memory_mode,
    is_ocean_timezone,
    method_timed,
    package_data_folder,
)
from .utils_numba import pt_in_poly_python
from .zone_names import get_zone_names_in_memory, get_zone_names_lazy

# TODO find out why this happens
# C:\Users\Jannis\AppData\Local\Continuum\Anaconda3\lib\site-packages\numba\ir_utils.py:1969:
# UserWarning: are_updates_precise(): precise updates safe only for decent builders
# UserWarning: are_updates_precise(): precise updates safe only for decent builders
# -> This warning is probably related to the one described here:
# https://github.com/numba/numba/issues/2933
warnings.filterwarnings("ignore", "are_updates_precise")

# call the JIT compiler to compile the python point-in-polygon function
# only if numba is installed and without raising any exceptions
pt_in_poly_python = njit_if_numba()(pt_in_poly_python)


class TimezoneFinder:
    """
    This class can be used to quickly find the timezone of a point on earth.
    It is thread-safe and can be used in a multithreaded environment.
    """

    # these are the class variables of the python implementation of the point in polygon check
    # inside_polygon is a wrapper for the different implementations of the point in polygon check
    # it is automatically chosen based on the availability of the C extension and Numba
    inside_polygon = None
    using_numba_speedup = False
    using_clang_speedup = False

    def __init__(
        self,
        in_memory: bool = get_in_memory_mode(),
        data_dir: Optional[Union[str, "Path"]] = None,
    ):
        """
        Create a new TimezoneFinder instance.

        :param in_memory: if all data should be read into memory now
        :param data_dir: Path to the directory with the timezone data files
        """
        # Make this instance thread-safe when using the C extension
        # (see https://cffi.readthedocs.io/en/latest/using.html#working-with-threads)
        # from .inside_poly_extension import inside_polygon_int
        # self.inside_polygon_C = ffi.thread_local(inside_polygon_int)

        self._in_memory = in_memory

        if data_dir is None:
            self._data_dir = package_data_folder
        else:
            self._data_dir = get_data_dir(data_dir)

        self._poly_data = None
        self._poly_coord_data = None
        self._poly_properties = None

        from .flatbuf.hex_zone_utils import get_hex_zone_file_path, read_hex_zone_data
        from .np_binary_helpers import read_numpy_from_file

        # open the shortcut file and parse it
        shortcut_path = get_shortcut_file_path(self._data_dir)
        if not shortcut_path.exists():
            raise FileNotFoundError(
                "The shortcut file cannot be found. Please make sure the timezone data is installed correctly."
            )
        self._shortcut_data: Dict[int, List[int]] = read_shortcut_data(shortcut_path)

        # open the hex zone file
        hex_zone_path = get_hex_zone_file_path(self._data_dir)
        if not hex_zone_path.exists():
            # This is not a critical error, maybe the data is old.
            # I can just work without it.
            self._hex_zone_data: Dict[int, int] = {}
        else:
            self._hex_zone_data: Dict[int, int] = read_hex_zone_data(hex_zone_path)

        if in_memory:
            # parse all data into memory
            (
                self._poly_data,
                self._poly_coord_data,
                self._poly_properties,
            ) = read_polygon_data(data_dir=self._data_dir, in_memory=True)
            self._zone_names = get_zone_names_in_memory(self._data_dir)
            self._poly_zone_ids: np.ndarray = read_numpy_from_file(
                self._data_dir, "zone_ids.npy"
            )
        else:
            self._zone_names = get_zone_names_lazy(self._data_dir)
            # only read the poly_zone_ids into memory, because they are needed for unique_timezone_at
            # and it is a small file
            self._poly_zone_ids: np.ndarray = read_numpy_from_file(
                self._data_dir, "zone_ids.npy"
            )

        # the most expensive function calls are cached
        # self.timezone_at = lru_cache(maxsize=128)(self.timezone_at)
        # self.timezone_at_land = lru_cache(maxsize=128)(self.timezone_at_land)

        # pre-compile the python function with numba
        # self.inside_polygon_python(0, 0, np.array([0, 0, 0, 0]))

    @classmethod
    def using_numba(cls) -> bool:
        """Returns True if the Numba JIT compiled version of the point in polygon algorithm is being used."""
        cls.__get_inside_polygon_func()
        return cls.using_numba_speedup

    @classmethod
    def using_clang_pip(cls) -> bool:
        """Returns True if the C compiled version of the point in polygon algorithm is being used."""
        cls.__get_inside_polygon_func()
        return cls.using_clang_speedup

    @classmethod
    def __get_inside_polygon_func(cls):
        # only set the function pointer once
        if cls.inside_polygon is None:
            # try using the numba compiled function
            if "signatures" in pt_in_poly_python.__dict__:
                cls.inside_polygon = pt_in_poly_python
                cls.using_numba_speedup = True
                return

            # try using the C-compiled function
            cls.inside_polygon = pt_in_poly_int
            cls.using_clang_speedup = True

    def _inside_window(self, lng: float, lat: float) -> bool:
        """
        Check if the coordinates are within the timezones bounding box.
        this is a shortcut to prevent lookups in the shortcut file, for points far away
        """
        return -180 <= lng <= 180 and -90 <= lat <= 90

    @method_timed
    def _get_timezone_name(
        self, lng: float, lat: float, *, search_in_memory: bool
    ) -> Optional[str]:
        """
        the main function for finding the timezone name.

        :param lng: longitude of the point in degree
        :param lat: latitude of the point in degree
        :param search_in_memory: if the polygons should be searched in the lists in memory
        :return: the timezone name of the polygon containing the point
        """
        # check if the coordinate is within the total bounding box
        if not self._inside_window(lng, lat):
            return None

        h3_id = h3.latlng_to_cell(lat, lng, H3_RESOLUTION)

        # check hex_zone shortcut
        zone_id = self._hex_zone_data.get(h3_id)
        if zone_id is not None:
            return self._zone_names[zone_id]

        polygon_indices = self._shortcut_data.get(h3_id)
        if polygon_indices is None:
            return None

        # get the polygons for the candidates
        polygons, poly_properties = get_coords_for_poly(
            polygon_indices,
            self._data_dir,
            self._poly_data,
            self._poly_coord_data,
            self._poly_properties,
            in_memory=search_in_memory,
        )

        # check if the point is in any of the polygons
        for i, p in enumerate(polygons):
            poly_id = polygon_indices[i]
            # properties of the polygon with the id poly_id
            # nr_of_holes, hole_coord_first_val, hole_coord_last_val
            poly_props = poly_properties[i]
            if poly_props is None:
                # no properties found for this polygon -> must be a polygon without holes
                if self.inside_polygon(lng, lat, p):
                    return self._zone_names[self._poly_zone_ids[poly_id]]
            else:
                # polygon with holes
                # check if the point is in the polygon
                if self.inside_polygon(lng, lat, p):
                    # check if the point is in any of the holes
                    if pt_in_poly_int_with_hole(
                        lng, lat, p, poly_props, self._poly_coord_data
                    ):
                        return self._zone_names[self._poly_zone_ids[poly_id]]

        return None

    def _get_unique_timezone_name(self, lng: float, lat: float) -> Optional[str]:
        """
        This is a much faster version of timezone_at.
        It returns the name of a unique timezone for the queried coordinates.
        This is only the case when the coordinate is not on a boundary of two timezones.
        In the case of a boundary None is returned.
        """
        h3_id = h3.latlng_to_cell(lat, lng, H3_RESOLUTION)
        zone_id = self._hex_zone_data.get(h3_id)
        if zone_id is not None:
            return self._zone_names[zone_id]

        # fallback for old data without hex_zone file
        if not self._hex_zone_data:
            polygon_indices = self._shortcut_data.get(h3_id)
            if polygon_indices is None:
                return None
            first_zone_id = self._poly_zone_ids[polygon_indices[0]]
            # check if all polygons in this shortcut belong to the same timezone
            for i in polygon_indices[1:]:
                if self._poly_zone_ids[i] != first_zone_id:
                    return None
            return self._zone_names[first_zone_id]

        return None

    def timezone_at(self, lng: float, lat: float) -> Optional[str]:
        """
        This is the default function to find the timezone of a point.

        :param lng: longitude of the point in degree (-180 to 180)
        :param lat: latitude of the point in degree (-90 to 90)
        :return: the timezone name of the polygon containing the point, or None
        """
        self.__get_inside_polygon_func()
        return self._get_timezone_name(lng=lng, lat=lat, search_in_memory=False)

    def timezone_at_land(self, lng: float, lat: float) -> Optional[str]:
        """
        This function is a wrapper for timezone_at.
        It returns None for all ocean timezones.

        :param lng: longitude of the point in degree
        :param lat: latitude of the point in degree
        :return: the timezone name of the polygon containing the point, or None
        """
        tz_name = self.timezone_at(lng=lng, lat=lat)
        if is_ocean_timezone(tz_name):
            return None
        return tz_name

    def certain_timezone_at(self, lng: float, lat: "float") -> Optional[str]:
        """
        This function is a wrapper for timezone_at.
        It returns the timezone name only if the point is certainly within in a timezone.
        If the point is on a boundary of two timezones, None is returned.
        This is useful for applications where you want to be sure about the timezone.

        :param lng: longitude of the point in degree
        :param lat: latitude of the point in degree
        :return: the timezone name of the polygon containing the point, or None
        """
        self.__get_inside_polygon_func()
        # TODO this only makes sense when using a different polygon data set, where the polygons are not overlapping
        # and the boundaries are not shared.
        return self.unique_timezone_at(lng=lng, lat=lat)

    def unique_timezone_at(self, lng: float, lat: float) -> Optional[str]:
        """
        This is the fastest version of timezone_at.
        It returns the name of a unique timezone for the queried coordinates.
        This is only the case when the coordinate is not on a boundary of two timezones.
        In the case of a boundary, None is returned.

        :param lng: longitude of the point in degree
        :param lat: latitude of the point in degree
        :return: the timezone name of the polygon containing the point, or None
        """
        # does not need polygon coordinates, so no need to select the search algorithm
        return self._get_unique_timezone_name(lng=lng, lat=lat)

    def get_geometry(
        self, tz_name: str = None, tz_id: int = None
    ) -> Optional[List[Dict]]:
        """
        :param tz_name: the name of a timezone
        :param tz_id: the id of a timezone
        :return: a list of GeoJSON compliant polygons (as python dicts) for a specific timezone
        or a list of all polygons, if no timezone is specified
        """
        if self._in_memory is False:
            (
                self._poly_data,
                self._poly_coord_data,
                self._poly_properties,
            ) = read_polygon_data(self._data_dir, in_memory=True)

        if tz_name is not None:
            if tz_name not in self._zone_names:
                raise ValueError(f"timezone {tz_name} is not in the list of zones")
            tz_id = self._zone_names.index(tz_name)

        if tz_id is not None:
            polygon_indices = [
                i for i, zone_id in enumerate(self._poly_zone_ids) if zone_id == tz_id
            ]
        else:
            # if no timezone is specified, return all polygons
            polygon_indices = list(range(len(self._poly_zone_ids)))

        polygons, poly_properties = get_coords_for_poly(
            polygon_indices,
            in_memory=True,
            poly_data=self._poly_data,
            poly_coord_data=self._poly_coord_data,
            poly_properties=self._poly_properties,
        )

        output = []
        for i, p in enumerate(polygons):
            poly_id = polygon_indices[i]
            geojson_dict = {
                "type": "Polygon",
                "coordinates": [],
                "properties": {"tz_name": self._zone_names[self._poly_zone_ids[poly_id]]},
            }

            # properties of the polygon with the id poly_id
            # nr_of_holes, hole_coord_first_val, hole_coord_last_val
            poly_props = poly_properties[i]

            if poly_props is None:
                # no properties found for this polygon -> must be a polygon without holes
                geojson_dict["coordinates"] = [p.tolist()]

            else:
                # polygon with holes
                all_hole_coords = []
                for hole_id in range(poly_props[0]):
                    hole_coords = self._poly_coord_data[
                        poly_props[1] + hole_id
                    ].tolist()
                    all_hole_coords.append(hole_coords)
                geojson_dict["coordinates"] = [p.tolist()] + all_hole_coords

            output.append(geojson_dict)

        return output


class TimezoneFinderL(TimezoneFinder):
    """
    This is a light version of the TimezoneFinder class.
    It is initialized with all data in memory and does not have the option to use files.
    This is useful for applications where you want to have a small memory footprint and fast startup time.
    So this class does not support the in_memory parameter and does not have file-based attributes.
    This class is thread-safe.
    """

    def __init__(self, data_dir: Optional[Union[str, "Path"]] = None):
        super().__init__(in_memory=True, data_dir=data_dir)
        self._shortcut_data = {}
        self._hex_zone_data = {}

    def timezone_at(self, lng: float, lat: float) -> Optional[str]:
        self.__get_inside_polygon_func()
        return self._get_timezone_name(lng=lng, lat=lat, search_in_memory=True)

    def unique_timezone_at(self, lng: float, lat: float) -> Optional[str]:
        # unique_timezone_at is not supported in the light version because no shortcuts are loaded
        return None