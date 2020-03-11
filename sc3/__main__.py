
import argparse
import sc3

parser = argparse.ArgumentParser()
parser.add_argument(
    '-m', '--mode', type=str, choices=['rt', 'nrt'], default='rt',
    help='set library running mode')
# TODO: opt lang bind port.
# TODO: opt logging verbosity.
args = parser.parse_args()


### Init library ###

sc3.init(args.mode)  # Init access point, custom values.
