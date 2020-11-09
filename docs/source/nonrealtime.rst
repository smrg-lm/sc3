.. _nonrealtime:

.. warning:: Under construction.

Non real time mode
==================

.. TODO (Also missing bits of the implementation).

The library can also run in non real time (NRT) mode. This mode is
based on the NRTClock quark with the addition that the whole library
timing is managed in NRT.

In NRT, clocks, routines and random generators work with the same
interface as real time. It was made so code can be easily adapted
or run in both modes without changes.

.. note::
   It's not possible to run the library in RT and NRT at the same time
   because clocks and :term:`elapsed time` are internally managed in
   different ways. To run a NRT script from a RT library instance could
   be done by creating a sub-process that starts a new interpreter.

::

  #!/usr/bin/env python3

  import time

  # Explicitly call sc3.init function.
  import sc3
  sc3.init('nrt')

  # All import as usual.
  from sc3.all import *

  @routine
  def r1():
      for i in range(3):
          yield 1

  @routine
  def r2():
      for i in range(4):
          yield 1

  clock1 = TempoClock(3)
  clock2 = TempoClock(4)

  r1.play(clock1)  # Fork!
  r2.play(clock2)  # Fork!
  et = main.elapsed_time()  # Will probably return 0.0 if evaluated
                            # before forked routines advance the time.
  print('elapse time before sleep:', et)

  time.sleep(2)  # Arbitrary processing wait time.
  et = main.elapsed_time()  # Will return 1.0.
  print('elapse time after sleep:', et)

.. Collection of OSC bundles.
