import logging
import collections
import os

from PIL import Image, ImageColor, ImageDraw, ImageFilter

from .colors import ColorMap
from .geo import PolyLine, Extent
from .heatmap import Heatmap, ScaledClusterer


log = logging.getLogger('gps_heatmap.renderers')


"""PIL/Pillow based heatmap renderer."""


def split_by_heat_value(line, heatmap, extent=None):
    """Split lines into segments with same Heatmap value.

    If Extent is given return only segments inside this extent.

    """
    prev_value = None
    segment = PolyLine()
    for point in line:
        if extent and not point in extent:
            if prev_value and segment:
                yield prev_value, segment
            prev_value = None
            segment = PolyLine()
            continue
        value = heatmap.get(point)
        if extent:
            point = extent.translate(point)
        segment.append(point)
        if prev_value and not value == prev_value:
            yield prev_value, segment
            segment = PolyLine()
            segment.append(point)
        prev_value = value
    if segment:
        yield prev_value, segment


class ImageRenderer(object):

    def __init__(self, lines, clusterer, extent=None, line_width=3):
        self.lines = lines
        self.clusterer = clusterer
        self.line_width = line_width
        self._extent = extent
        self._heatmap = None
        self._normalized_heatmap = None

    @property
    def extent(self):
        if not self._extent:
            extent = Extent.from_lines(self.lines, margin=100)
            log.info('Extent: %s, size: %d x %d', extent, extent.width, extent.height)
            self._extent = extent
        return self._extent

    @property
    def heatmap(self):
        """Return normalized heatmap."""
        if not self._normalized_heatmap:
            if not self._heatmap:
                heatmap = Heatmap.from_lines(self.clusterer, self.lines)
                log.info('Heatmap len=%d, min=%d, max=%d', 
                         len(heatmap), heatmap.min_value, heatmap.max_value)
                self._heatmap = heatmap
            log.info('Clustering and normalizing heatmap values...')
            heatmap = self._heatmap.normalize_log()
            log.info('Heatmap len=%d, min=%s, max=%s', 
                     len(heatmap), heatmap.min_value, heatmap.max_value)
            self._normalized_heatmap = heatmap
        return self._normalized_heatmap

    def update(self, lines, update_extent=False):
        self._normalized_heatmap = None
        if update_extent:
            self._extent = None
        count = 0
        for line in lines:
            count += 1
            self.lines.append(line)
            self._heatmap.update(line)
        heatmap = self._heatmap
        log.info('Heatmap len=%d, min=%d, max=%d', 
                 len(heatmap), heatmap.min_value, heatmap.max_value)
        log.info('Updated with %d lines', count)

    def color_lines_gen(self, color_map):
        for line in self.lines:
            for value, line_segment in split_by_heat_value(line, self.heatmap, self.extent):
                color = color_map.get(value)
                yield color, line_segment

    def plot_lines(self, color_map):
        image = Image.new('RGBA', self.extent.size)
        draw = ImageDraw.Draw(image)
        for color, line in self.color_lines_gen(color_map):
            draw.line(line, color.rgba, self.line_width)
        # NOTE: Flip image, as PIL coordinates starts at top-left!
        image = image.transpose(Image.FLIP_TOP_BOTTOM)
        return image

    def plot_points(self, color_map):
        image = Image.new('RGBA', self.extent.size)
        draw = ImageDraw.Draw(image)
        for point, value in self.heatmap:
            color = color_map.get(value)
            point = self.extent.translate(point)
            radius = self.line_width/2
            draw.ellipse((point.x-radius, point.y-radius, point.x+radius, point.y+radius), color.rgba)
        # NOTE: Flip image, as PIL coordinates starts at top-left!
        image = image.transpose(Image.FLIP_TOP_BOTTOM)
        return image



class Renderer(object):

    #BLUR_RADIUS = [16, 8, 4, 1]
    BLUR_RADIUS = [10, 5, 1]
    CM_STEPS = 256

    def __init__(self, lines_ts, clusterer, 
                 hsva_min, hsva_max, steps=CM_STEPS, 
                 background_color=None, 
                 line_width=3,
                 extent_margin=100,
                 blur_radius=BLUR_RADIUS):
        self.lines_ts = lines_ts
        self.clusterer = clusterer
        self.color_map = None
        self.set_color_map(hsva_min, hsva_max, steps)
        self.background_color = background_color
        self.line_width = line_width
        self.extent_margin = extent_margin
        self._extent = None
        self.blur_radius = blur_radius

    def post_process(self, image):
        result = None
        for radius in self.blur_radius:
            if not radius:
                continue
            log.debug('Blurring with radius %d', radius)
            blur = image.filter(ImageFilter.GaussianBlur(radius))
            if result:
                result = Image.alpha_composite(result, blur)
            else:
                result = blur
        return result

    def composite(self, *images):
        if self.background_color:
            size = images[0].size
            result = Image.new('RGBA', size, self.background_color.rgb)
        else:
            result = None
        for image in images:
            if not result:
                result = image
            else:
                result = Image.alpha_composite(result, self.post_process(image))
        return result

    @property
    def extent(self):
        if not self._extent:
            extent = Extent.from_lines(self.lines_ts, self.extent_margin)
            log.info('Extent: %s, size: %d x %d', extent, extent.width, extent.height)
            self._extent = extent
        return self._extent

    def set_color_map(self, hsva_min, hsva_max, steps=CM_STEPS):
        self.color_map = ColorMap.from_gradient(hsva_min, hsva_max, steps)

    def get_image_renderer(self, lines):
        return ImageRenderer(lines, self.clusterer, self.extent, self.line_width)

    def get_path(self, base, group_name, group, group_format=None):
        fn = [base, ]
        fn.append(group_name)
        if group:
            if group_format and isinstance(group, collections.Iterable):
                fn.append(group_format % tuple(group))
            elif group_format:
                fn.append(group_format % group)
            elif isinstance(group, collections.Iterable):
                fn.append('_'.join(str(e) for e in group))
            else:
                fn.append(str(group))
        #fn.append(self.clusterer.__class__.__name__)
        fn = '__'.join(fn) + '.png'
        if group:
            if not os.path.exists(group_name):
                os.mkdir(group_name)
            path = os.path.join(group_name, fn)
        else:
            path = fn
        return path

    def render_groups(self, base, group_name, group_format=None, cumulative=True):
        image_renderer = None
        for group, lines in getattr(self.lines_ts, group_name):
            log.info('Heatmap for %s - adding %d lines', group or group_name, len(lines))
            if image_renderer and cumulative:
                image_renderer.update(lines)
            else:
                image_renderer = self.get_image_renderer(lines)
            image = image_renderer.plot_lines(self.color_map)
            #image = image_renderer.plot_points(self.color_map)
            result = self.composite(image)
            if not cumulative:
                group_name = group_name.replace('ly', 's')
            path = self.get_path(base, group_name, group, group_format)
            result.save(path)

    def render(self, output_fn='heatmap.png'):
        image_renderer = self.get_image_renderer(self.lines_ts)
        image = image_renderer.plot_lines(self.color_map)
        #image = image_renderer.plot_points(self.color_map)
        result = self.composite(image)
        result.save(output_fn)

    def render_all(self, base='heatmap'):
        self.render_groups(base, 'all')

    def render_yearly(self, base='heatmap'):
        self.render_groups(base, 'yearly', '%d')

    def render_quarterly(self, base='heatmap'):
        self.render_groups(base, 'quarterly', '%d-%d')

    def render_monthly(self, base='heatmap'):
        self.render_groups(base, 'monthly', '%d-%02d')

    def render_years(self, base='heatmap'):
        self.render_groups(base, 'yearly', '%d', cumulative=False)

    def render_quarters(self, base='heatmap'):
        self.render_groups(base, 'quarterly', '%d-%d', cumulative=False)

    def render_months(self, base='heatmap'):
        self.render_groups(base, 'monthly', '%d-%02d', cumulative=False)

