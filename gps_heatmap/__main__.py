from . import geo
from . import heatmap
from .main import BACKGROUND, COLOR_STEPS, LINE_WIDTH, EXTENT_MARGIN, HSVA_MIN, HSVA_MAX, SCALE
from .main import main


PROJECTION = 'mercator'

CLUSTERER = 'gaussian'
CLUSTER_SCALE = 3
CLUSTER_RADIUS = 5

GROUPS = [
    'years', 'yearly',
    'quarters', 'quarterly',
    'months', 'monthly',
    #'weeks', 'weekly',
]


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description="Render GPS heatmap")

    parser.add_argument('-v', '--verbose', action='store_true', default=False,
                        help="be more verbose")

    parser.add_argument('-g', '--group', dest='groups', action='append',
                        choices=GROUPS,
                        help="output groups")
    parser.add_argument('-o', '--output', metavar='FILE', #required=True,
                        help="output file")
    parser.add_argument('--max_gap', type=int, metavar='METERS', default=geo.MAX_GAP,
                        help="max gap between coordinates, default: %(default)s")

    group = parser.add_argument_group('Projection')
    group.add_argument('-p', '--projection', 
                        choices=sorted(geo.PROJECTIONS.keys()), default=PROJECTION,
                        help="map projection, default: %(default)s")
    group.add_argument('-s', '--scale', type=float, default=SCALE,
                        help="projection scale in meters per pixel, default: %(default)s"),

    group = parser.add_argument_group('Colors', 
                                      'colors as #RRGGBBaa or #HHHSSVVaa, alpha is optional')
    group.add_argument('-m', '--hsva_min', metavar='HEX', default=HSVA_MIN.hex,
                        help="min color, default: %(default)s")
    group.add_argument('-M', '--hsva_max', metavar='HEX', default=HSVA_MAX.hex,
                        help="max color, default: %(default)s")
    group.add_argument('--steps', type=int, default=COLOR_STEPS,
                        help="color map steps, default: %(default)s"),
    group.add_argument('-b', '--background', metavar='HEX', default=BACKGROUND.hex,
                        help="background color, default: %(default)s")
    parser.add_argument('-t', '--transparent', action='store_true', default=False,
                        help="no background, transparent image")

    group = parser.add_argument_group('Heatmap clustering')
    group.add_argument('-c', '--clusterer', 
                        choices=sorted(heatmap.CLUSTERERS.keys()), default=CLUSTERER,
                        help="heatmap clusterer, default: %(default)s")
    group.add_argument('-S', '--cluster_scale', type=float, default=CLUSTER_SCALE,
                        help="cluster_scale for scaled clusterer, default: %(default)s"),
    group.add_argument('-R', '--cluster_radius', type=int, default=CLUSTER_RADIUS,
                        help="cluster_scale for linear and gaussian clusterer, default: %(default)s"),

    group = parser.add_argument_group('Image rendering')
    group.add_argument('-l', '--line', type=int, metavar='WIDTH', default=LINE_WIDTH,
                        help="line width, default: %(default)s")
    group.add_argument('--margin', type=int, default=EXTENT_MARGIN,
                        help="image margin, default: %(default)s")
    group.add_argument('--blur', metavar='RADIUS', type=int, action='append',
                        help="Gaussian blur radius for post-processing, default: [10, 5, 1]")

    parser.add_argument('files', nargs='*', metavar='FILE',
                        help="input files")

    args = parser.parse_args()

    if not args.files:
        parser.error('No input files specified!')

    main(args)


