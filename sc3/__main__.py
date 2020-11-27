
import argparse
import logging
import sys
import runpy

import sc3


parser = argparse.ArgumentParser(prog='sc3')

parser.add_argument(
    '-v', '--version', action='version',
    version=f'%(prog)s {sc3.__version__}')
parser.add_argument(
    '-N', '--nrt', action='store_const', const='nrt',
    help='non real time mode')
parser.add_argument(
    '-u', '--udp-port', type=int, default=57120,
    help='udp library port')
parser.add_argument(
    '-r', '--port-range', type=int, default=10,
    help='udp available port range')
parser.add_argument(
    '-s', '--setup-file', type=str, default=None,
    help='library setup.py file')
parser.add_argument(
    '-V', '--verbosity', type=int, default=20,
    help='logger level')
parser.add_argument('file', nargs='?')
parser.add_argument('args', nargs=argparse.REMAINDER)

args = parser.parse_args()


### Config library ###

sc3.LIB_MODE = args.nrt or 'rt'
sc3.LIB_PORT = args.udp_port
sc3.LIB_PORT_RANGE = args.port_range
sc3.LIB_SETUP_FILE = args.setup_file


### Init library ###

sc3.init(sc3.LIB_MODE, logging.getLevelName(args.verbosity))


### Run script ###

if args.file:
    sys.argv = [args.file, *args.args]  # Simulate script args.
    runpy.run_path(args.file)
