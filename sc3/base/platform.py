"""Platform.sc"""

from pathlib import Path
import tempfile
import os
import sys
# import site
import subprocess
import threading

from . import classlibrary as clb


clb.ClassLibrary.late_imports(__name__, ('sc3.base.main', '_libsc3'))


__all__ = ['Platform']


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

    @property
    def installation_dir(cls):
        return _libsc3.main.platform.installation_dir

    @installation_dir.setter
    def installation_dir(cls, value):
        _libsc3.main.platform.installation_dir = value

    @property
    def bin_dir(cls):
        return _libsc3.main.platform.bin_dir

    @property
    def default_server_cmd(cls):
        return _libsc3.main.platform.default_server_cmd

    @property
    def SCSYNTH_CMD(cls):
        return _libsc3.main.platform.SCSYNTH_CMD

    @property
    def SUPERNOVA_CMD(cls):
        return _libsc3.main.platform.SUPERNOVA_CMD

    @staticmethod
    def _cmd_line(*popenargs, sync=False):  # sclang unixCmd no pid return.
        if sync:
            subprocess.call(*popenargs)
        else:
            run = lambda: subprocess.call(*popenargs)
            threading.Thread(target=run, daemon=True).start()

    def killall(cls, program_name):
        '''
        Kill a server process by name. Utility method used to stop a lost
        server in the local machine, e.g. when is not possible to reboot or
        connect and the process is retaining the port.
        On Unix this method executes ``killall -SIGKILL program_name``.
        On Windows it executes ``taskkill /F /IM program_name``.
        '''
        return _libsc3.main.platform.killall(program_name)


class Platform(metaclass=MetaPlatform):
    def _startup(self):
        pass

    def _shutdown(self):
        pass

    @property
    def name(self):
        '''The name of the platform as returned by `sys.platform`.'''
        return sys.platform

    @property
    def home_dir(self):  # Was userHomeDir.
        '''User home directory.'''
        return Path.home()

    @property
    def support_dir(self):  # Was userAppSupportDir.
        '''The directory containing SuperCollider user resources.'''
        raise NotImplementedError

    @property
    def config_dir(self):  # Was userConfigDir.
        '''The directory containing SuperCollider user configuration.'''
        raise NotImplementedError

    @property
    def resource_dir(self):  # userAppSupportDir.
        '''The directory containing SuperCollider installation resources.'''
        raise NotImplementedError

    @property
    def synthdef_dir(self):
        '''The directory where synthdef files are sotred by default.'''
        raise NotImplementedError

    @property
    def recording_dir(self):
        '''The directory where recording files are sotred by default.'''
        raise NotImplementedError

    @property
    def tmp_dir(self):
        '''The temporal directory, set to system default `tmp` directory.'''
        return Path(tempfile.gettempdir())

    @property
    def installation_dir(self):
        '''Installation directory, in OSX it's the app bundle.'''
        return Path(self._installation_dir)

    @installation_dir.setter
    def installation_dir(self, value):
        # Attribute _installation_dir and os.environ['PATH'] mut be
        # properly initialized by _startup().
        old_path_dir = str(self.bin_dir)
        self._installation_dir = str(value)
        os.environ['PATH'] = os.environ['PATH'].replace(
            old_path_dir, str(self.bin_dir))

    @property
    def bin_dir(self):
        '''The directory where the server programs are located.'''
        raise NotImplementedError


class UnixPlatform(Platform):
    SCSYNTH_CMD = 'scsynth'
    SUPERNOVA_CMD = 'supernova'

    def killall(self, program_name):
        cmd = ['killall', '-9', program_name]
        type(self)._cmd_line(cmd)


class LinuxPlatform(UnixPlatform):
    def _startup(self):
        # // default jack port hookup
        os.environ['SC_JACK_DEFAULT_INPUTS'] = 'system'
        os.environ['SC_JACK_DEFAULT_OUTPUTS'] = 'system'
        # // automatically start jack when booting the server
        # // can still be overridden with JACK_NO_START_SERVER
        os.environ['JACK_START_SERVER'] = 'true'

        self._installation_dir = '/usr'  # whereis scsynth ../
        os.environ['PATH'] += os.pathsep + str(self.bin_dir)
        self.default_server_cmd = self.SCSYNTH_CMD
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
        return self.installation_dir / Path('share/SuperCollider')

    @property
    def synthdef_dir(self):
        return self.support_dir / Path('synthdefs')

    @property
    def recording_dir(self):
        return self.support_dir / Path('Recordings')

    @property
    def bin_dir(self):
        return self.installation_dir / Path('bin')


class DarwinPlatform(UnixPlatform):
    def _startup(self):
        self._installation_dir = '/Applications/SuperCollider.app'
        os.environ['PATH'] += os.pathsep + str(self.bin_dir)
        self.default_server_cmd = self.SCSYNTH_CMD

    @property
    def support_dir(self):
        return self.home_dir / Path('Library/Application Support/SuperCollider')

    @property
    def config_dir(self):
        return self.home_dir / Path('Library/Application Support/SuperCollider')

    @property
    def resource_dir(self):
        return self.installation_dir / Path('Contents/Resources')

    @property
    def synthdef_dir(self):
        return self.support_dir / Path('synthdefs')

    @property
    def recording_dir(self):
        return self.home / Path('Music/SuperCollider Recordings')

    @property
    def bin_dir(self):
        return self.resource_dir


class WindowsPlatform(Platform):
    SCSYNTH_CMD = 'scsynth.exe'
    SUPERNOVA_CMD = 'supernova.exe'

    def killall(self, program_name):
        cmd = ['taskkill', '/F', '/IM', program_name]
        type(self)._cmd_line(cmd)


class Win32Platform(WindowsPlatform):
    def _startup(self):
        from . import _knownpaths as kp

        self._local_app_data = kp.get_path(kp.FOLDERID.LocalAppData, 0)
        self._documents = kp.get_path(kp.FOLDERID.Documents, 0)

        program_files_x86 = kp.get_path(kp.FOLDERID.ProgramFilesX86, 0)
        program_files_x64 = kp.get_path(kp.FOLDERID.ProgramFilesX64, 0)
        folders = list(Path(program_files_x86).glob('SuperCollider*'))
        folders += list(Path(program_files_x64).glob('SuperCollider*'))

        self._installation_dir = str(self._get_lastest_version(folders))
        os.environ['PATH'] += str(self.bin_dir) + os.pathsep
        self.default_server_cmd = self.SCSYNTH_CMD
        # // load user startup file
        # self.load_startup_file()

    def _shutdown(self):
        pass

    @staticmethod
    def _get_lastest_version(path_list):
        # Get the folder with the lastest version.
        # Folder name format sould be 'SuperCollider-X.X.X'.
        res = []
        for path in path_list:
            name = path.name
            version = name.split('-')[1]
            version = version.split('.')
            version = [int(n) for n in version if n.isdigit()]
            res.append((version, path))
        return sorted(res, key=lambda x: x[0])[-1][1]

    @property
    def support_dir(self):
        return Path(self._local_app_data) / Path('SuperCollider')

    @property
    def config_dir(self):
        return self.support_dir()

    @property
    def resource_dir(self):
        return self.installation_dir

    @property
    def synthdef_dir(self):
        return self.support_dir / Path('synthdefs')

    @property
    def recording_dir(self):
        return Path(self._documents) / Path('Recordings')

    @property
    def bin_dir(self):
        return self.installation_dir


class CygwinPlatform(WindowsPlatform):
    ...
