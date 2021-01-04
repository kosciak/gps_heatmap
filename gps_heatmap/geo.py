import collections
import logging
import math


log = logging.getLogger('gps_heatmap.loaders')


"""Geometry and geography related data types and functions."""


MAX_GAP = 700

AVG_EARTH_RADIUS = 6371000  # Avarege earth radius in meters
METERS_PER_DEGREE = 2 * math.pi * AVG_EARTH_RADIUS / 360


class Coord(collections.namedtuple('Coord', ['x', 'y'])):

    """Base Coordinate class."""

    __slots__ = ()

    def distance(self, other):
        if not other:
            return None
        x = self.x - other.x
        y = self.y - other.y
        return math.sqrt(x**2 + y**2)

    def __repr__(self):
        return '<%s x=%s, y=%s>' % (self.__class__.__name__, self.x, self.y)


class Point(Coord):

    """Point with x, and y as integers."""

    __slots__ = ()

    def __new__(cls, x, y):
        return Coord.__new__(cls, int(round(x)), int(round(y)))


class LatLon(Coord):

    """Geographic Coordinate with longitute and latitude as degrees."""

    __slots__ = ()

    @property
    def lat(self):
        return self.x

    @property
    def latitude(self):
        return self.x

    @property
    def lon(self):
        return self.y

    @property
    def longitude(self):
        return self.y

    def distance(self, other):
        """Return distance (in meters) to other LatLon coordinate.

        For performance reasons distance is calculated using Equirectangular approximation.
        For most cases, and small distances this should be close enough to exaxt distance.
        If exact distance is need Haversine formula should be used.

        See: https://en.wikipedia.org/wiki/Haversine_formula

        """
        if not other:
            return None
        coef = math.cos(math.radians(self.lat))
        x = self.lat - other.lat
        y = (self.lon - other.lon) * coef
        return math.hypot(x, y) * METERS_PER_DEGREE

    def __repr__(self):
        return '<%s lat=%s, lon=%s>' % (self.__class__.__name__, self.x, self.y)


class Extent(object):

    def __init__(self, coords=None):
        self.min = None
        self.max = None
        if coords:
            self.update(coords)

    def update(self, coords):
        max_x = max(coord.x for coord in coords)
        min_x = min(coord.x for coord in coords)
        max_y = max(coord.y for coord in coords)
        min_y = min(coord.y for coord in coords)
        coord_cls = self.max and self.max.__class__ or coords[0].__class__
        self.max = coord_cls(self.max and max(self.max.x, max_x) or max_x, 
                             self.max and max(self.max.y, max_y) or max_y)
        self.min = coord_cls(self.min and min(self.min.x, min_x) or min_x, 
                             self.min and min(self.min.y, min_y) or min_y)

    def resize(self, size):
        coord_cls = self.max.__class__
        return Extent([
            coord_cls(self.max.x + size, self.max.y + size),
            coord_cls(self.min.x - size, self.min.y - size)
        ])

    @staticmethod
    def from_lines(lines, margin=None):
        extent = Extent()
        for line in lines:
            extent.update(line)
        if margin:
            extent = extent.resize(margin)
        return extent

    @property
    def width(self):
        return self.max.x - self.min.x + 1

    @property
    def height(self):
        return self.max.y - self.min.y + 1

    @property
    def size(self):
        return self.width, self.height

    def translate(self, coord):
        """Return Coord with x and y relative to extent.min."""
        coord_cls = self.max.__class__
        return self.max.__class__(coord.x - self.min.x, coord.y - self.min.y)

    def is_inside(self, coord):
        """Return True if given Coord is inside extent."""
        return (self.min.x <= coord.x <= self.max.x and
                self.min.y <= coord.y <= self.max.y)

    def __contains__(self, coord):
        return self.is_inside(coord)

    def __iter__(self):
        yield self.min
        yield self.max

    def __repr__(self):
        return '<%s min=%r, max=%r>' % (self.__class__.__name__, self.min, self.max)


class PolyLine(object):

    """List of coordinates."""

    def __init__(self):
        self.coords = []

    def append(self, coord):
        if (self.coords and not self.coords[-1] == coord) or not self.coords:
            self.coords.append(coord)

    def extend(self, coords):
        for coord in coords:
            self.append(coord)

    @property
    def extent(self):
        if self.coords:
            return Extent(self.coords)

    def __len__(self):
        return len(self.coords)

    def __getitem__(self, key):
        return self.coords[key]

    def __iter__(self):
        for coord in self.coords:
            yield coord


class Projection(object):

    """Base class for geographic projection implementations.

    Child classes must implement project() method.

    """

    EARTH_RADIUS = AVG_EARTH_RADIUS # Avarege earth radius in meters

    def __init__(self, scale):
        self.meters_per_degree = 2 * math.pi * self.EARTH_RADIUS / 360
        self.meters_per_radian = math.degrees(self.meters_per_degree)
        self._pixels_per_degree = None
        self._pixels_per_radian = None
        self.set_meters_per_pixel(scale)

    @property
    def pixels_per_degree(self):
        return self._pixels_per_degree

    @property
    def pixels_per_radian(self):
        return self._pixels_per_radian

    def set_pixels_per_degree(self, value):
        self._pixels_per_degree = value
        self._pixels_per_radian = math.degrees(self.pixels_per_degree)

    @property
    def meters_per_pixel(self):
        return self.meters_per_degree / self.pixels_per_degree

    @property
    def scale(self):
        return self.meters_per_pixel

    def set_meters_per_pixel(self, value):
        self.set_pixels_per_degree(self.meters_per_degree / value)

    def project(self, latlon):
        raise NotImplementedError

    def project_meters(self, latlon):
        coord = self.project(latlon)
        return Coord(coord.x*self.meters_per_pixel, coord.y*self.meters_per_pixel)


class EquirectangularProjection(Projection):

    """Equirectangular projection.

    See: http://en.wikipedia.org/wiki/Equirectangular_projection

    """

    def project(self, latlon):
        x = latlon.lon * self.pixels_per_degree
        y = latlon.lat * self.pixels_per_degree
        return Coord(x, y)


class WebMercatorProjection(Projection):

    """WGS 84 Web Mercator / Spherical Mercator projection used by Google Maps.

    See: https://en.wikipedia.org/wiki/Mercator_projection
         https://en.wikipedia.org/wiki/Web_Mercator

    """

    EARTH_RADIUS = 6378137  # Approximate Earth radius used in Web Mercator

    def project(self, latlon):
        x = latlon.lon * self.pixels_per_degree
        y = self.pixels_per_radian * math.log(
            math.tan(math.pi/4 + math.radians(latlon.lat/2)))
        return Coord(x, y)

# Set as alias
MercatorProjection = WebMercatorProjection


PROJECTIONS = {
    'equirectangular': EquirectangularProjection,
    'mercator': WebMercatorProjection,
}


def get_lines(activity, projection, max_gap=MAX_GAP):
    """Return PolyLines from given activity using provided Projection.

    If distance between two coordinates in activity is greater than max_gap split
    activity into separate polylines. This way we can remove strange artifacts 
    when we moved when activity was paused.

    """
    line = PolyLine()
    prev_latlon = None
    for latlon in activity:
        distance = latlon.distance(prev_latlon)
        prev_latlon = latlon
        if distance and distance > max_gap:
            log.warning('Splitting! distance: %d > %d max gap', distance, max_gap)
            if line:
                yield line
            line = PolyLine()
        coord = Point(*projection.project(latlon))
        line.append(coord)
    yield line

