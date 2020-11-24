.. _basicserver:

Basic server configuration and usage
====================================

To make use of the library you need to have the SuperCollider
server installed. The easiest way to download and install the
latest release for your platform. The Python library will search
for the server in the default locations and make use of the same
platform and user resources and configuration folders.

On Linux there are pre-compiled Debian packages and servers can be
installed as independent programs (useful for SoC platforms).

::

  sudo apt install supercollider-supernova  # simd server
  sudo apt install supercollider-server  # or install scsynth

Any server will do and that is the only dependency of sc3.

.. note:
   By default, sc3 will search for the servers in the default
   installation locations or will work without configuration
   if the server programs are in the PATH.


Custom server location
----------------------

If the server is installed in a non standard location ...

::

  Platform.installation_dir = '/usr/local/bin'  # Linux
  Platform.installation_dir = '/my/path/to/SuperCollider.app'  # OSX
  Platform.installation_dir = r'c:\my\path\SuperCollider-X.Y.Z'  # Windows

Alternatively the full path to the server program can be set
in server options:

::

  s.options.program = '/path/to/supernova'  # Unix
  s.options.program = r'c:\path\to\supernova.exe'  # Windows


Making configuration persistent
-------------------------------

Default server options can be made persistent by using a startup
file located at ``Platform.config_dir``. The place to create
that file can is returned by the following expression:

::

  Platform.config_dir / 'setup.py'

And the content of `setup.py` may look like this:

::
  from sc3.base.platform import Platform
  from sc3.synth.server import s

  Platform.installation_dir = '/usr/local'

  s.options.program = 'scsynth'
  s.options.input_channels = 4
  s.options.output_channels = 8
  s.options.sample_rate = 96000

.. note:
   In the setup file imports must be absolute and
   `from sc3.all import *` will not work.

.. warning:
   Start up file is for basic configuration only, by now it is
   a Python script but it may change to a more specific format in
   the future.


Server usage
------------

Once the server is installed it has to be booted within an
interactive session or in a script to be ready for receiving
synthesis definitions and events. By default, a default Server
object is instantiated and assigned to a global variable ``s``
which is available when importing ``sc3.all``.

::

  from sc3.all import *
  s.boot()

By default, the server is configured to use the port 57110 and
the library uses the first available between 57120 and 57129.
If there is no port conflict and the audio interface is properly
configured a message will be displayed indication that the
server was booted successfully and the client was given an id.
The server port can be viewed and changed from the ``s.addr``
attribute.

To test if it sounds you can try:

::

  play()

To test your speakers you can do:

::

  play(instr='test', out=0)  # Fist channel.
  play(instr='test', out=1)  # Second channel.
  play(instr='test', out=2)  # Third...
  ...

To quit the server used ``s.quit()``. There are also methods for
``reboot`` the local server, and ``register`` to a remote server.

.. note
   When using booth :term:`sclang` and this library it may happen that
   an already starter server program is using the default port, in the
   reference to that server was lost it can be killed from the client
   with ``Platform.killall('supernova')``.
