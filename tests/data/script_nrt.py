import argparse
from sc3.all import *

parser = argparse.ArgumentParser(prog='sc3')
parser.add_argument('script_arg', nargs='?')
args = parser.parse_args()

prefix = 'script_nrt FAILED:'

if args.script_arg != 'TEST_ARG_VALUE':
    sys.exit(f'{prefix}: TEST_ARG_VALUE')  # Fist test.

SystemDefs.add_sdef('default')

@routine.run()
def r():
    for i in range(3):
        play()
        yield 1

osc_score = main.process()
if len(osc_score.list) != 9:
    sys.exit(f'{prefix}: Score length')  # Second test.

if s.options.inputs != 4 or s.options.outputs != 8\
or s.options.program != 'supernova':
    sys.exit(f'{prefix}: Server options')  # Third test.
