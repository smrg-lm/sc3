"""SystemSynthDefs.sc"""

from ..base import platform as plf
from . import synthdef as sdf
from . import ugens as ugns


class SystemSynthDefs():
    num_channels = 16
    tmp_name_prefix = 'tmp__'
    max_tmp_def_names = 512
    _tmp_def_count = 0

    def __new__(cls):
        return cls

    @classmethod
    def generate_tmp_name(cls):  # moved to SynthDef.
        name = cls.tmp_name_prefix + str(cls._tmp_def_count)
        cls._tmp_def_count += 1
        cls._tmp_def_count %= cls.max_tmp_def_names
        return name

    @classmethod
    def _init_class(cls):  # BUG: A MetaSystemSynthDefs? def init del init? at all?
        # NOTE: JITLib specific.
        # StartUp.add -> _init_class
        path = plf.Platform.synthdef_dir
        match = list(path.glob(cls.tmp_name_prefix + '*'))
        if match:
            _logger.info(f'celaning up temporary synthdefs, {len(match)} found')
            for file in match:
                file.unlink()

        for i in range(1, cls.num_channels + 1):
            def _(out=0, input=16, vol=1, level=1, lag=0.05, done_action=2):
                env = ...  # EnvGate adds magic controls.
                ...
            sdf.SynthDef('system_link_audio_' + i, _, ['kr'] * 5 + ['ir'])

            ...
