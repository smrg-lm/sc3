.. sc3 documentation master file, created by
   sphinx-quickstart on Sun Nov 10 10:26:02 2019.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

sc3
===

Port of core features from sclang to Python 3, 3.6 for sure maybe >= 3.5 (not
tested). It is intended to be the same library in a different language and to
keep sclang elegance in a pythonic way (if possible).

So far SynthDef compiles and Routine and TempoClock are barely working, for
that I started form AbstractFunction. Basics are not finished, I’m still
studding the code. Also I’m not being linear in feature transcription, more
like jumping and iterating (revisiting and completing) from place to place so
to have the whole picture, sclang library has features integrated from bottom
up and between classes. Everything is in a very early stage.

Code is still full of study comments and references (very unprofessional, I
know) most of them useless, don’t try understand, those are just reminders to
myself. I will be erasing them gradually. Some original sclang comments were
kept in code with two slash within python comments (``# //``) and each file has
a reference to the source (many are obvious but some are not and some names
were changed for different reasons).

The main reason for this port is Python's capacity of interaction with other
libraries applicable to composition, sonic-art and alike, and to be able to
compile synth definitions and send them to the server is very handy.

I still don't know what would be the scope regarding features, what I will get
finished for sure are server abstractions and interaction.


Isn't Python slow?
------------------

Yes it is and so is sclang, the problem would be realtimeness and that's solved
the same way for Python [TODO: brief explanation of logical time, interaction
with the server and time boundaries].


Example
-------

The idea is that you can write the same in Python as in sclang, with the same
logic regarding multichannel expansion, arguments conversion to Control ugens,
etc., it should be the same result. For example::

		from sc3.all import *

		# interactive shell run...

		s = Server.local
		s.boot()

		# wait or error...

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


That's a working example but many things are not finished or tested and some
are no decided, things may change or move.


Install (in develop mode)
-------------------------

::

		python3 setup.py develop --user


Contribute
----------

- Issue Tracker: https://github.com/smrg-lm/sc3/issues
- Source Code: https://github.com/smrg-lm/sc3

Support
-------

If you are having issues, please let us know.


License
-------

The sc3 library holds the same license as SuperCollider: sc3 is free software
available under Version 3 of the GNU General Public License. See COPYING for
details.


Contents
========

.. toctree::
   :maxdepth: 2

   License <license>
   Authors <authors>
   Changelog <changelog>
   Module Reference <api/modules>


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
