.. _glossary:

********
Glossary
********

.. if you add new entries, keep the alphabetical sorting!
.. TODO: preliminar draft written from memory, needs review and to be completed.

.. glossary::

   add action
      An action number that defines the insertion behavior of a node.

   audio rate
      The sampling rate of the server.

   asynchronous command
      Commands performed by the server outside the real time thread.
      Asynchronous commands send a reply to the registered clients
      when the task is completed.

   block size
      The size, in samples, of the control rate processing interval
      of the server.

   buffer
      Dynamically allocated memory in the server used to store audio
      data. Buffers are used to load audio files and may have different
      sample rates.
      See :class:`Buffer<sc3.synth.buffer.Buffer>`.

   bus
      A server bus used to connect ugens in different synth nodes.
      Server's buses are global and ugens write or read from them in
      the order defined by their position in the node tree.

   completion message
      An OSC message sent as a binary blob to some asynchronous server
      commands. These messages are evaluated after the task of the
      command is finished.

   control rate
      The rate introduced by csound to perform less computation for
      signals that don't require sample rate accuracy. It's used to
      reduce the CPU load.

   default group
      A server group created by the client application after the server
      is booted. Default group ID is always 1 and is the user default
      target group.

   demand rate
      A control or audio rate signal that changes at frequency defined
      by `demand` ugens.
      See :class:`Demand<sc3.synth.ugens.Demand>`.

   done action
      An action performed in the server by certain ugens when finish.
      Done actions can free or pause server nodes relative to the
      ugen that fires it.
      See :class:`Done<sc3.synth.ugens.Done>`.

   elapsed time
      In real time is the :term:`physical time` in seconds since the
      library start. In non real time is the total time in seconds
      advanced by routines playing on clocks.

   group
      A group in the server tree.
      See :class:`Group<sc3.synth.node.Group>`.

   initial rate
      An special rate that computes values only at initialization.

   logical time
      The time as measured by :class:`Routine<sc3.base.stream.Routine>`
      instances. Logical time is measured in deterministic interval
      and is not affected by jitter as :term:`physical time`. It's
      used to precisely define the :term:`timetag` for OSC bundles.

   multichannel expansion:
      Because SuperCollider represents multiple channels as lists of ugens,
      when an ugen receives a list of values for one or more of its input arguments
      the constructor returns a :class:`ChannelList<sc3.synth.ugen.ChannelList>`
      object containing one ugen instance for each element in the longest list
      instead of a single ugen. The shortest lists are wrapped to fit the length
      of the longest and passed in order to the different instances, scalar
      values are kept as the argument of each new instance. This special behavior,
      along with the operations over lists of channels, is a convenient way to
      expand graphs and maintain a simple representation by avoiding loops.

   node
      A server tree node.
      See :class:`Node<sc3.synth.node.Node>`.

   physical time
      The time as measured by the computer's system clock. When used as
      wait time is subject to jitter, it depends on non deterministic
      processing time between calls and is affected by NTP adjustments.

   quark
      A SuperCollider extension library written in :term:`sclang`.

   root node
      The root node group of a server's node tree.
      The id of the root node is always 0.
      See :class:`RootGroup<sc3.synth.node.RootGroup>`.

   sclang
      The original language of SuperCollider.

   scsynth
      The original server of SuperCollider.

   supernova
      An new alternative implementation of the server with SIMD
      capabilities and parallel group processing.

   synth
      A synthesis node.
      See :class:`Synth<sc3.synth.node.Synth>`.

   synthdef
      A synthesis definition composed of ugens used to create synth
      nodes.
      See :class:`SynthDef<sc3.synth.synthdef.SynthDef>`.

   timetag
      An OSC-timetag. It's the time at which bundled instructions are
      scheduled to be executed in the server. Although the term is used
      to refer to the time of bundles, within the library time is measured
      in seconds (or beats for :class:`TempoClock<sc3.base.clock.TempoClock>`)
      relative to :term:`elapsed time` and is converted to the actual
      timetag representation when sent.

   trigger
      An impulsive signal that is created when the value of a bus goes
      from being less than or equal to to being greater than zero.

   trigger rate
      A control rate signal that behaves like an impulse, when set
      to a value it returns to zero immediately after.

   ugen
      A sound synthesis processing unit.

   wire buffer
      An internal connection between two ugens. Number of wires is
      defined at boot time.
