import logging

import srtm


log = logging.getLogger('gps_heatmap.utils')


def remove_waypoints(gpx):
    """Remove all waypoints."""
    gpx.waypoints = []
    return gpx


def fix_elevation(gpx):
    """Fix elevation data using SRTM database."""
    elevation_data = srtm.get_data()
    elevation_data.add_elevations(gpx, smooth=True)
    return gpx
