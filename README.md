![PyPI - Python Version](https://img.shields.io/pypi/pyversions/sc3)
![PyPI](https://img.shields.io/pypi/v/sc3)

sc3
===

Port of core features from SuperCollider's language to Python 3. It is intended to be the same library in a different language and to keep sclang elegance in a pythonic way (if possible).

The main reason for this port is Python's capacity of interaction with other libraries applicable to composition, sonic-art and research. My wish is for this project to be useful for the SuperCollider community.

Note that this project is still under development and there are missing parts, bugs you are welcome to report, and is no such a thing like "documentation" here by now. The best way to learn about SuperCollider is going to the [source](https://supercollider.github.io).

Example
-------

The idea is that you can write the same in Python as in sclang, with the same logic regarding multichannel expansion, arguments conversion to Control ugens, etc., it should be the same result. For example:

```python
from sc3.all import *

# interactive shell run...

s.boot()

@synthdef.add()
def sine(freq=440, amp=0.1, gate=1):
    sig = SinOsc.ar(freq) * amp
    sig *= EnvGen.kr(Env.adsr(), gate, done_action=2)
    Out.ar(0, sig.dup())

sine.dump_ugens()

# following lines are meant to be executed one by one as in interactive
# session. Commands to the server are asynchronous actions that need a bit
# of time for the resource to be available/changed.

n = Synth('sine')
n.set('amp', 0.05)
n.set('freq', 220)

s.query_tree(True)

n.release()
# s.free_all()  # if something went wrong free all nodes.

s.quit()  # stop server at the end of interactive session or just quit ipython.
```

Install
-------

From PyPI:

```
pip3 install sc3
```

From source in develop mode:

```
python3 setup.py develop --user
```

License
-------

The sc3 library holds the same license as SuperCollider: sc3 is free software available under Version 3 of the GNU General Public License. See [COPYING](COPYING) for details.
