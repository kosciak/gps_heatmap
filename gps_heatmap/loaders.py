import logging
import datetime
import glob
import os

import gpxpy

from .geo import LatLon, Point, get_lines


log = logging.getLogger('gps_heatmap.loaders')


"""Load data from various sources."""


class ActivityType(object):

    """ Type of the activity."""

    RUN = 'Run'
    RIDE = 'Ride'
    NA = 'N/A'


class Activity(object):

    """Activity consisting of LatLon coords."""

    def __init__(self, filename, name, date, activity_type):
        self.filename = filename
        self.name = name
        self.type = activity_type
        self.date = date
        self.latlons = [] # = [LatLon, ...]

    def append(self, latlon):
        self.latlons.append(latlon)

    def __iter__(self):
        for latlon in self.latlons:
            yield latlon

    @property
    def distance(self):
        distance = 0
        prev_latlon = None
        for latlon in self.latlons:
            if prev_latlon:
                distance += latlon.distance(prev_latlon)
            prev_latlon = latlon
        return distance

    @property
    def avg_distance(self):
        return self.distance / len(self.latlons)

    def __len__(self):
        return len(self.latlons)

    def __repr__(self):
        return '<Activity %s fn=%r name=%r>' % (self.type, self.filename, self.name)


class GPXFileLoader(object):

    """Loads Activities from GPX files."""

    def read_file(self, fn):
        base_fn = os.path.basename(fn)
        base_root, ext = os.path.splitext(base_fn)
        if base_root.endswith('-Run') or base_root.endswith('-Running'):
            activity_type = ActivityType.RUN
        elif base_root.endswith('-Ride') or base_root.endswith('-Cycling'):
            activity_type = ActivityType.RIDE
        else:
            activity_type = ActivityType.NA
        gpx_file = open(fn, 'r')
        gpx = gpxpy.parse(gpx_file)
        date = gpx.time
        if date is None:
            stat = os.stat(fn)
            tz = gpxpy.gpxfield.SimpleTZ()
            date = datetime.datetime.fromtimestamp(stat.st_mtime, tz)
        for track in gpx.tracks:
            for track_segment in track.segments:
                activity = Activity(fn, track.name, date, activity_type)
                for point in track_segment.points:
                    activity.append(LatLon(point.latitude, point.longitude))
                yield activity


LOADERS = {
    '.gpx': GPXFileLoader(),
}


def read_files(fns):
    for fn in sorted(fns):
        fn_root, ext = os.path.splitext(fn)
        loader = LOADERS.get(ext)
        if not loader:
            log.warning('Unknown file format: %s', fn)
            continue
        for activity in loader.read_file(fn):
            yield activity


def read_pattern(fns_pattern):
    fns = glob.glob(fns_pattern)
    for activity in read_files(fns):
        yield activity


def read(fns=None, fns_pattern=None):
    if fns:
        for activity in read_files(fns):
            yield activity
    if fns_pattern:
        for activity in read_pattern(fns_pattern):
            yield activity

