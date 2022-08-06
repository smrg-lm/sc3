
from subprocess import run
from sys import exit
from pathlib import Path

# Most tests need to start a new interpreter and
# must run sequentially if using the server.

path = Path(__file__).parent
files = [f for f in path.glob('test_*.py') if f.is_file]

for test in files:
    ret = run(['python', str(test)])
    if ret.returncode:
        exit(ret.returncode)
