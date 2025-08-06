import pytest
from timezonefinder import TimezoneFinder


class TestIssue30:
    @pytest.fixture(scope="class")
    def tf(self):
        """Initializes the TimezoneFinder class with the latest data"""
        return TimezoneFinder()

    def test_get_geometry_for_all_zones(self, tf):
        """
        Tests that get_geometry() runs for all zones without crashing and returns a list.
        This is important because some polygons might be deleted as part of the unique zone optimization.
        For zones where all polygons have been deleted, an empty list is expected.
        """
        for tz_name in tf.timezone_names:
            geometries = tf.get_geometry(tz_name=tz_name)
            assert isinstance(geometries, list)
