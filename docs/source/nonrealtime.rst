.. _nonrealtime:

.. warning:: Under construction.

Non real time mode
==================

The library can also run in non real time (NRT) mode. This mode is
based on the NRTClock quark with the addition that the whole library
timing is managed in NRT.

In NRT, clocks, routines and random generators work with the same
interface as real time. It was made so code can be easily adapted
or run in both modes without changes.

.. note::
   It's not possible to run the library in both RT and NRT at the
   same time because clocks and :term:`elapsed time` are internally
   managed in different ways. To run a NRT script from a RT library
   instance could be done by creating a sub-process that starts a
   new interpreter.

The following example can be run as command line script:

::

  #!/usr/bin/env python3

  import sc3
  sc3.init('nrt')  # Needs to be initialized in NRT before all star import.
  from sc3.all import *

  # Load default synthdef.
  SystemDefs.add_sdef('default')

  @routine
  def r1():
      for n in [58, 62, 64, 69, 60, 66, 73]:
          play(midinote=n, sustain=2)
          yield 1

  r1.play(TempoClock(3))

  # Generate the OSC score.
  score = main.process(2)
  # Elapsed time is the sum of all yielded values without last delay.
  print('elapsed time =', main.elapsed_time())
  # Dump OSC commands score.
  print(score)
  # Render the score.
  score.render('test.aiff')

.. Collection of OSC bundles.
