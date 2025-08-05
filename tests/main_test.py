import unittest
from pathlib import Path
from unittest import mock
import numpy as np

from timezonefinder.timezonefinder import TimezoneFinder
from timezonefinder import utils
from . import auxiliaries

# number of points to test for each zone
NR_TEST_POINTS = 10

# number of test points for the speed test
NR_SPEED_TEST_POINTS = 1000


class TestTimezoneFinder(unittest.TestCase):
    # a backup of the original Timezonefinder class
    tf_backup = TimezoneFinder
    # create one TimezoneFinder instance for all tests
    # this is being created in the setUpClass method
    tf = None
    # path to the test data
    test_data_path = Path(__file__).parent / "test_data"
    test_files_path = Path(__file__).parent / "test_files"

    @classmethod
    def setUpClass(cls) -> None:
        # preparations for the tests must be made here
        # create one instance of the class with all data loaded
        cls.tf = cls.get_instance()

    @classmethod
    def get_instance(cls, *args, **kwargs) -> TimezoneFinder:
        return TimezoneFinder(*args, **kwargs)

    def test_unique_timezone_at_with_new_shortcut(self):
        # test the new optimization for unique_timezone_at
        tf = self.get_instance()

        # h3.latlng_to_cell(52, 13, 4) -> 614334544569565183
        # Let's say Europe/Berlin is zone_id 150 (example, not real)
        berlin_hex = 614334544569565183
        berlin_zone_id = 150
        # h3.latlng_to_cell(50, 6, 4) -> 614343104278429695 (near border)
        border_hex = 614343104278429695

        test_mapping = {berlin_hex: berlin_zone_id}
        with mock.patch.object(tf, "hex_zone_mapping", test_mapping):
            with mock.patch.object(
                TimezoneFinder,
                "zone_name_from_id",
                lambda slf, x: "Europe/Berlin" if x == berlin_zone_id else "Error",
            ):
                with mock.patch(
                    "timezonefinder.timezonefinder.h3.latlng_to_cell"
                ) as mock_h3:
                    # Test case 1: Hit -> should return timezone name
                    mock_h3.return_value = berlin_hex
                    self.assertEqual(
                        tf.unique_timezone_at(lng=13, lat=52), "Europe/Berlin"
                    )

                    # Test case 2: Miss -> should return None because it's not in the mocked map
                    mock_h3.return_value = border_hex
                    self.assertIsNone(tf.unique_timezone_at(lng=6, lat=50))

    def test_timezone_at_with_unique_zone_shortcut(self):
        # test that timezone_at uses the new optimization
        tf = self.get_instance()
        # h3.latlng_to_cell(52, 13, 4) -> 614334544569565183
        berlin_hex = 614334544569565183
        berlin_zone_id = 150
        test_mapping = {berlin_hex: berlin_zone_id}

        # Mock the shortcut mapping and the expensive check to make sure they are NOT called
        # when the new optimization is hit.
        with mock.patch.object(tf, "hex_zone_mapping", test_mapping):
            with mock.patch.object(
                TimezoneFinder,
                "zone_name_from_id",
                lambda slf, x: "Europe/Berlin" if x == berlin_zone_id else "Error",
            ):
                with mock.patch(
                    "timezonefinder.timezonefinder.h3.latlng_to_cell"
                ) as mock_h3:
                    with mock.patch.object(
                        TimezoneFinder, "get_boundaries_in_shortcut"
                    ) as mock_get_boundaries:
                        mock_h3.return_value = berlin_hex
                        self.assertEqual(tf.timezone_at(lng=13, lat=52), "Europe/Berlin")
                        # Assert that the old logic was NOT called
                        mock_get_boundaries.assert_not_called()

    def test_kwargs(self):
        self.assertEqual(self.tf.timezone_at(lng=13.358, lat=52.5061), "Europe/Berlin")

    def test_packaging(self):
        # TODO
        pass

    def test_readme_examples(self):
        self.assertEqual(self.tf.timezone_at(lng=13.358, lat=52.5061), "Europe/Berlin")
        # certain_timezone_at
        self.assertEqual(
            self.tf.certain_timezone_at(lng=13.358, lat=52.5061), "Europe/Berlin"
        )

    def test_from_file(self):
        # test initializing from a file

        # create a TimezoneFinder instance from file
        in_memory_mode = [True, False]
        for in_memory in in_memory_mode:
            self.get_instance(in_memory=in_memory)

    def test_shortcut_boundary_data(self):
        # LNG: 13.358166, LAT: 52.506136
        # -> polygon captions should be checked:
        # tz_id=150: Europe/Berlin
        # tz_id=149: Europe/Busingen
        # tz_id=130: Europe/Amsterdam
        # -> result should be Europe/Berlin
        lng = 13.358166
        lat = 52.506136

        expected_tz_name = "Europe/Berlin"

        self.assertEqual(self.tf.timezone_at(lng=lng, lat=lat), expected_tz_name)
        self.assertEqual(
            self.tf.certain_timezone_at(lng=lng, lat=lat), expected_tz_name
        )
        self.assertEqual(
            self.tf.unique_timezone_at(lng=lng, lat=lat), "Europe/Berlin"
        )

        # test for a point in a zone with only one polygon candidate:
        # LNG: 12.89, LAT: 48.52
        # tz_id=150: Europe/Berlin
        # -> result should be Europe/Berlin
        self.assertEqual(self.tf.timezone_at(lng=12.89, lat=48.52), "Europe/Berlin")

    def test_hole_data(self):
        # coords of a hole in Africa/Johannesburg timezone
        lng = 28.31
        lat = -26.1
        self.assertEqual(self.tf.timezone_at(lng=lng, lat=lat), "Africa/Maseru")

    def test_ocean_data(self):
        # test a point in the ocean, should return correct ocean timezone
        self.assertEqual(self.tf.timezone_at(lng=0, lat=0), "Etc/GMT")

    def test_invalid_coordinates(self):
        # coordinates must be checked for validity
        self.assertRaises(ValueError, self.tf.timezone_at, lng=181, lat=52.5)
        self.assertRaises(ValueError, self.tf.timezone_at, lng=-181, lat=52.5)
        self.assertRaises(ValueError, self.tf.timezone_at, lng=13.3, lat=91)
        self.assertRaises(ValueError, self.tf.timezone_at, lng=13.3, lat=-91)

    # def test_correctness(self):
    #     # tests for every timezone if the found timezone name is correct
    #     for zone_name in self.tf.timezone_names:
    #         print("testing: ", zone_name)
    #         test_cases = auxiliaries.get_test_points(
    #             zone_name=zone_name, nr_of_points=NR_TEST_POINTS
    #         )
    #         for lng, lat in test_cases:
    #             self.assertEqual(zone_name, self.tf.timezone_at(lng=lng, lat=lat))

    def test_certain_timezone_at(self):
        # coordinates outside of any timezone. With ocean data, this should find something.
        self.assertIsNotNone(self.tf.certain_timezone_at(lng=-52.5, lat=85))

    def test_get_geometry(self):
        # just test if get_geometry runs without errors,
        # TODO proper testing of the output
        self.tf.get_geometry(tz_name="Europe/Berlin")
        # self.tf.get_geometry(tz_id=0) # This call is ambiguous and fails
        self.tf.get_geometry(tz_id=0, use_id=True)
        self.tf.get_geometry(tz_name="Europe/Berlin", coords_as_pairs=True)
        # should raise an error for invalid name
        self.assertRaises(ValueError, self.tf.get_geometry, tz_name="non existing")
        # should raise an error for invalid id
        self.assertRaises(ValueError, self.tf.get_geometry, tz_id=-1, use_id=True)
        self.assertRaises(
            ValueError, self.tf.get_geometry, tz_id=10000, use_id=True
        )

    def test_inside_polygon(self):
        lng = 13.358166
        lat = 52.506136

        possible_polygons = self.tf.get_boundaries_in_shortcut(lng=lng, lat=lat)

        x = utils.coord2int(lng)
        y = utils.coord2int(lat)

        self.assertTrue(self.tf.inside_of_polygon(possible_polygons[0], x, y))

    def test_compile(self):
        """
        python setup.py build_ext --inplace
        nosetests --with-coverage
        :return:
        """
        # TODO
        pass

    def test_converter(self):
        # TODO
        pass

    def test_all_included_files_being_used(self):
        # TODO
        pass


if __name__ == "__main__":
    unittest.main()
