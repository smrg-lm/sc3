"""Platform.sc"""

from pathlib import Path
import tempfile
import os
import sys
# import site

from . import main as _libsc3
from ..synth import server as srv
# from ..synth import score as sco


class MetaPlatform(type):
    @property
    def name(cls):
        return sys.platform

    @property
    def home_dir(cls):
        return _libsc3.main.platform.home_dir

    @property
    def support_dir(cls):
        return _libsc3.main.platform.support_dir

    @property
    def config_dir(cls):
        return _libsc3.main.platform.config_dir

    @property
    def resource_dir(cls):
        return _libsc3.main.platform.resource_dir

    @property
    def synthdef_dir(cls):
        return _libsc3.main.platform.synthdef_dir

    @property
    def recording_dir(cls):
        return _libsc3.main.platform.recording_dir

    @property
    def tmp_dir(cls):
        return _libsc3.main.platform.tmp_dir


class Platform(metaclass=MetaPlatform):
    # default_startup_file = ...  # *initClass this.userConfigDir +/+ "startup.scd"

    def _startup(self):
        pass

    def _shutdown(self):
        pass

    @property
    def name(self):
        return sys.platform

    @property
    def home_dir(self):
        return Path.home()

    @property
    def support_dir(self):  # userAppSupportDir
        raise NotImplementedError()

    @property
    def config_dir(self):
        raise NotImplementedError()

    @property
    def resource_dir(self):  # userAppSupportDir/supportDir
        raise NotImplementedError()

    @property
    def synthdef_dir(self):
        raise NotImplementedError()

    @property
    def recording_dir(self):
        raise NotImplementedError()

    @property
    def tmp_dir(self):
        return Path(tempfile.gettempdir())


class UnixPlatform(Platform):
    pass


class LinuxPlatform(UnixPlatform):
    def _startup(self):
        srv.Server.program = 'scsynth'
        # sco.Score.program = srv.Server.program
        # // default jack port hookup
        os.environ['SC_JACK_DEFAULT_INPUTS'] = 'system'
        os.environ['SC_JACK_DEFAULT_OUTPUTS'] = 'system'
        # // automatically start jack when booting the server
        # // can still be overridden with JACK_NO_START_SERVER
        os.environ['JACK_START_SERVER'] = 'true'
        # // load user startup file
        # self.load_startup_file()

    def _shutdown(self):
        pass

    @property
    def support_dir(self):
        return self.home_dir / Path('.local/share/SuperCollider')

    @property
    def config_dir(self):
        return self.home_dir / Path('.config/SuperCollider')

    @property
    def resource_dir(self):
        ...  # /usr/local/share/SuperCollider: sounds, examples, HID_Support, etc.

    @property
    def synthdef_dir(self):
        return self.support_dir / Path('synthdefs')

    @property
    def recording_dir(self):
        return self.support_dir / Path('Recordings')


class OSXPlatform(UnixPlatform):
    ...


class WindowsPlatform(Platform):
    pass


class Win32Platform(WindowsPlatform):
    ...


class CygwinPlatform(WindowsPlatform):
    ...
