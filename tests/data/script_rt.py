from sc3.all import *

parser = argparse.ArgumentParser(prog='sc3')
parser.add_argument('script_arg', nargs='?')
args = parser.parse_args()

prefix = 'script_rt FAILED:'

if args.script_arg != 'TEST_ARG_VALUE':
    sys.exit(f'{prefix}: TEST_ARG_VALUE')  # Fist test.

if s.options.inputs != 4 or s.options.outputs != 8\
or s.options.program != 'supernova':
    sys.exit(f'{prefix}: Server options')  # Seconds test.

if hasattr(main, 'process'):
    sys.exit(f'{prefix}: Server mode')  # Third test.
