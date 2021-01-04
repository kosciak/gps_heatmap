import collections
import math

from .geo import Point


class Heatmap(object):

    def __init__(self, clusterer=None):
        self.clusterer = clusterer or Clusterer()
        self.points = collections.Counter()

    def __getitem__(self, point):
        return self.points[point]

    def __setitem__(self, point, value):
        self.points[point] = value

    def get(self, point):
        point = self.clusterer.cluster_point(point)
        return self.points.get(point, 0)

    def __len__(self):
        return len(self.points)

    def __iter__(self):
        return self.points.items()

    @property
    def min_value(self):
        return min(self.points.values())

    @property
    def max_value(self):
        return max(self.points.values())

    def update(self, line):
        line = self.clusterer.cluster_points(line)
        for point in line:
            self.points[point] += 1

    def normalize(self, norm_func=None):
        """Return normalized Heatmap with max value = 1.0"""
        clustered = self.clusterer.cluster_heatmap(self)
        max_value = clustered.max_value
        if norm_func:
            max_value = norm_func(max_value, max_value)
        normalized = Heatmap(self.clusterer)
        for point, value in clustered.points.items():
            if norm_func:
                value = norm_func(value, max_value)
            normalized[point] = value*1./max_value
        return normalized

    def normalize_log(self):
        return self.normalize(lambda value, max_value: math.log(value+1))

    def get_histogram(self):
        """Return number of points per heat value."""
        histogram = collections.Counter()
        for point, value in self.points.items():
            histogram[value] += 1
        return histogram

    @classmethod
    def from_lines(cls, clusterer, lines):
        """Create Heatmap from Lines."""
        heatmap = Heatmap(clusterer)
        for line in lines:
            heatmap.update(line)
        return heatmap


class Clusterer(object):

    def cluster_point(self, point):
        return point

    def cluster_points(self, line):
        for point in line:
            yield point

    def cluster_heatmap(self, heatmap):
        return heatmap


class ScaledClusterer(Clusterer):

    def __init__(self, cluster_scale, count_cluster_point_once=True, *args, **kwargs):
        self.cluster_scale = cluster_scale
        if self.cluster_scale > 1.0:
            self.cluster_scale = 1. / self.cluster_scale
        self.count_cluster_point_once = count_cluster_point_once

    def cluster_point(self, point):
        return Point(point.x*self.cluster_scale, point.y*self.cluster_scale)

    def cluster_points(self, line):
        prev_cluster_point = None
        for point in line:
            cluster_point = self.cluster_point(point)
            if self.count_cluster_point_once:
                if not cluster_point == prev_cluster_point:
                    yield cluster_point
            else:
                yield cluster_point
            prev_cluster_point = cluster_point


class OnceScaledClusterer(ScaledClusterer):

    def __init__(self, cluster_scale, *args, **kwargs):
        ScaledClusterer.__init__(self, cluster_scale, True)


class MultiScaledClusterer(ScaledClusterer):

    def __init__(self, cluster_scale, *args, **kwargs):
        ScaledClusterer.__init__(self, cluster_scale, False)


class KernelClusterer(Clusterer):

    def __init__(self, radius, *args, **kwargs):
        self.radius = radius
        self._weights_matrix = {} # = {(x, y): weight, ...}

    def get_weight(self, distance):
        raise NotImplementedError()

    @property
    def weights_matrix(self):
        if not self._weights_matrix:
            for x in range(-self.radius, self.radius+1):
                for y in range(-self.radius, self.radius+1):
                    distance = math.hypot(x, y)
                    weight = self.get_weight(distance)
                    if weight:
                        self._weights_matrix[(x, y)] = weight
        return self._weights_matrix

    def points(self, point):
        for (x, y), weight in self.weights_matrix.items():
            yield Point(point.x+x, point.y+y), weight

    def cluster_heatmap(self, heatmap):
        clustered = Heatmap(self)
        for point, value in heatmap.points.items():
            clustered_value = 0
            for kernel_point, weight in self.points(point):
                value = heatmap.points[kernel_point]
                if value:
                    clustered_value += value * weight
            clustered[point] = clustered_value
        return clustered


class LinearKernelClusterer(KernelClusterer):

    def get_weight(self, distance):
        if distance >= self.radius:
            return 0
        return 1. - (distance / self.radius)


class GaussianKernelClusterer(KernelClusterer):

    def __init__(self, radius, *args, **kwargs):
        KernelClusterer.__init__(self, radius)
        self.scale = math.log(256) / radius

    def get_weight(self, distance):
        if distance >= self.radius:
            return 0
        return math.e ** (-distance * self.scale)


CLUSTERERS = {
    'none': Clusterer,
    'linear': LinearKernelClusterer,
    'gaussian': GaussianKernelClusterer,
    'scaled': OnceScaledClusterer,
}
