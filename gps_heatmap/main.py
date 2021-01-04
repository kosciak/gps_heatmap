import logging

from . import loaders
from . import geo
from . import heatmap
from . import colors
from .renderers import Renderer
from .timeseries import Timeseries


log = logging.getLogger('gps_heatmap.loaders')


# TODO: Move to defaults.py ?
SCALE = 30

HSVA_MIN = colors.RED.set_alpha(96)
HSVA_MAX = colors.YELLOW

COLOR_STEPS = 5
COLOR_STEPS = 16
COLOR_STEPS = 32
#COLOR_STEPS = 64

BACKGROUND = colors.BLACK

LINE_WIDTH = 3

LINE_WIDTH = 3

BLUR_RADIUS = [10, 5, 1]

EXTENT_MARGIN = 100



def load_lines_ts(fns=None, fns_pattern=None,
                  projection=None, scale=SCALE, max_gap=geo.MAX_GAP):
    if not projection:
        projection = geo.MercatorProjection(scale=scale)
    lines_ts = Timeseries()
    for activity in loaders.read(fns=fns, fns_pattern=fns_pattern):
        log.info('Parsing: %s', activity)
        log.debug('avg_distance: %.2f', activity.avg_distance)
        for line in geo.get_lines(activity, projection, max_gap):
            lines_ts.add(activity.date, line)
    return lines_ts


def get_renderer(lines_ts, clusterer=None, background=True):
    background_color = None
    if background:
        background_color = BACKGROUND
    renderer = Renderer(lines_ts, clusterer, 
                        HSVA_MIN, HSVA_MAX, steps=COLOR_STEPS, 
                        background_color=background_color,
                        line_width=LINE_WIDTH)
    return renderer


def render(lines_ts):
    clusterers = [
        heatmap.Clusterer(), 
        heatmap.OnceScaledClusterer(3), 
        heatmap.MultiScaledClusterer(3), 
        heatmap.LinearKernelClusterer(3),
        heatmap.GaussianKernelClusterer(5),
    ]
    for clusterer in clusterers:
        log.info('Render using: %s', clusterer.__class__.__name__)
        renderer = get_renderer(lines_ts, clusterer)
        renderer.render_all()


def main(args):
    level = logging.INFO
    if args.verbose:
        level = logging.DEBUG
    logging.basicConfig(level=level,
                        format="%(asctime)s - %(levelname)s - %(message)s")

    projection = geo.PROJECTIONS[args.projection](args.scale)
    lines_ts = load_lines_ts(fns=args.files, projection=projection, max_gap=args.max_gap)
    clusterer = heatmap.CLUSTERERS[args.clusterer](cluster_scale=args.cluster_scale, 
                                                   radius=args.cluster_radius)
    hsva_min = colors.HEX(args.hsva_min)
    hsva_max = colors.HEX(args.hsva_max)
    background = None
    if not args.transparent:
        background = colors.HEX(args.background)
    renderer = Renderer(lines_ts, clusterer, 
                        hsva_min=hsva_min, hsva_max=hsva_max, steps=args.steps,
                        background_color=background, 
                        line_width=args.line,
                        extent_margin=args.margin,
                        blur_radius=args.blur or BLUR_RADIUS)
    if args.output:
        renderer.render(args.output)
    for group in args.groups or []:
        render_func = getattr(renderer, 'render_%s' % group)
        render_func()

