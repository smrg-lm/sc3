sc3
===

Port of core features from sclang to Python 3, 3.6 for sure maybe >= 3.5 (not
tested). It is intended to be the same library in a different language and to
keep sclang elegance in a pythonic way (if possible).

So far SynthDef compiles and Routine and TempoClock are barely working, for that
I started form AbstractFunction. Basics are not finished, I’m still studding the
code. Also I’m not being linear in feature transcription, more like jumping and
iterating (revisiting and completing) from place to place so to have the whole
picture, sclang library has features integrated from bottom up and between
classes. Everything is in a very early stage.

Code is still full of study comments and references (very unprofessional, I
know) most of them useless, don’t try understand, those are just reminders to
myself. I will be erasing them gradually. Some original sclang comments were
kept in code with two slash within python comments (`# //`) and each file has a
reference to the source (many are obvious but some are not and some names were
changed for different reasons).

The main reason for this port is Python's capacity of interaction with other
libraries applicable to composition, sonic-art and alike, and to be able to
compile synth definitions and send them to the server is very handy.

I still don't know what would be the scope regarding features, what I will get
finished for sure are server abstractions and interaction. The first idea was to
transcribe patterns too, sounds easy, but patterns and events are a big deal for
many reasons.

Python is not a real time language, it has much more jitter than sclang. While
in my laptop sclang maintains an average 0.1ms time drift peak between calls
with Python I have peaks of 5ms which is quite a lot. A pure Python
implementation will not solve that and I don’t have intentions to go low level
by now. It is not that it is impossible but that it is out of my scope.

It is not really a deal breaker for many use cases because SuperCollider
algorithms sync routines time no matter what but if you use routines to
sequence musical events non real time code will produce rhythmic irregularities
(soft real time degradation) if the system is a bit loaded and specially if code
is complex and make many calls, and even less than 1ms is too much when it
starts to add.

Having said that, the idea is that you can write the same in Python as in
sclang, with the same logic regarding multichannel expansion, arguments
conversion to Control ugens, etc., it should be the same result. For example:

```python
from sc3.all import *

# interactive shell run...

s = Server.local
s.boot()

# wait or error...

@synthdef.add()
def sine(freq=440, amp=0.1, gate=1):
    osc = SinOsc.ar([freq, freq + 1], mul=amp)
    env = Linen.kr(gate, done_action=2)
    Out.ar(0, osc * env)

sine.dump_ugens()

# wait or error, manually connect jack meanwhile...

n = Synth('sine')
n.set('amp', 0.05)
n.set('freq', 220)
s.query_all_nodes(True)
n.release()
s.quit()
```

That's a working example but many things are not finished or tested and some are
no decided, things may change or move.

Install (in develop mode)
-------------------------

```
python3 setup.py develop --user
```

License
-------

sc3 holds the same license as its origin: SuperCollider is free software
available under Version 3 of the GNU General Public License. See
[COPYING](COPYING) for details.
