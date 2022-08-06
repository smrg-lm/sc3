
from subprocess import run
from sys import exit
from pathlib import Path

# Most tests need to start a new interpreter and
# must run sequentially if using the server.

path = Path(__file__).parent
files = [f for f in path.glob('test_*.py') if f.is_file]
sep = '*' * 70

for test in files:
    print(f'{sep}\nTest file: {test.name}\n{sep}')
    errno = run(['python', str(test)]).returncode
    if errno:
        exit(errno)
