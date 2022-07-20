[![PyPI](https://img.shields.io/pypi/v/sc3)](https://pypi.org/project/sc3)
[![Documentation Status](https://readthedocs.org/projects/sc3/badge/?version=latest)](https://sc3.readthedocs.io/en/latest/?badge=latest)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/sc3)

SuperCollider library for Python
================================

This project is a port of core features of SuperCollider's language to Python 3. It is intended to be the same library in a different language and to keep sclang elegance in a pythonic way (if possible).

The main reason for this port is Python's capacity of interaction with other libraries applicable to composition, sonic-art and research. My wish is for this project to be useful for the SuperCollider community.

Note that this project is still under development and there are missing parts, bugs you are welcome to report, and documentation is under construction. The best way to learn about SuperCollider is going to the [source](https://supercollider.github.io).

Examples
--------

The idea is that you can write the same in Python as in sclang, with the same logic regarding multichannel expansion, arguments conversion to Control ugens, etc., it should be the same result. For example:

```python
from sc3.all import *

s.boot()

@synthdef
def sine(freq=440, amp=0.1, gate=1):
    sig = SinOsc(freq) * amp
    env = EnvGen(Env.adsr(), gate, done_action=2)
    Out(0, (sig * env).dup())

sine.dump_ugens()
```

Wait for boot...

```python
n = Synth('sine')
```
```python
n.set('amp', 0.05)
```
```python
n.set('freq', 550)
```
```python
s.dump_tree(True)
```
```python
n.release()
# s.free_nodes()  # If something went wrong free all nodes.
```
```python
s.quit()  # Stop server at the end of interactive session or just quit ipython.
```

More examples can be found as python notebooks in the following repo:

[https://github.com/pabloriera/SC3_notebooks](https://github.com/pabloriera/SC3_notebooks)

Install
-------

Depending on your operating system you may need to use `python3` and `pip3`
commands instead of `python` and `pip`.

From source using pip (recomended by now):

```bash
pip install git+https://github.com/smrg-lm/sc3.git
```

Or with optional MIDI support:

```bash
pip install "sc3[midi] @ git+https://github.com/smrg-lm/sc3.git"
```

From source in develop mode (having a clone of this repo already):

```bash
python setup.py develop
```

For optional MIDI support also install mido and rtmidi backend:

```bash
pip install mido python-rtmidi
```

From PyPI (usually outdated by now, there will be a more stable beta version soon):

```bash
pip install sc3  # [midi] or [midi-nrt] for MIDI support, the nrt variant
                 # installs mido but not the driver.
```

License
-------

The sc3 library is free software available under Version 3 of the GNU General Public License. See [COPYING](COPYING) for details.

NB: The sc3 library is a Python translation of the SuperCollider's library and inherits its same license and community guidelines.
