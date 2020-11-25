"""Signal.sc"""

from ..base._hooks import opt_import, requires

numpy = opt_import('numpyc')

# *** NOTE: Tal vez debería sacar ClassLibrary y poner todo en _hooks.

# *** NOTE: No implementar WaveTable por separado.
# O implementar solo WaveTable para convertir los ndarrays.

# install_requires = ["numpy"],  # No.
# extras_require = {"numpy": ["numpy"]}  # Ok.


class Signal():
    @requires(numpy)
    def test(self):
        print('test')
