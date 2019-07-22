"""Env.sc"""

from . import graphparam as gpp


class Env(gpp.UGenParameter, gpp.NodeParameter):
    # TODO: todo.

    # BUG: si se necesita que sea general para otras clases hacer también __iter__?
    # BUG: y que EnvGen siempre reciba un array de tuplas en envelope
    # BUG: (como está hecho en sclang), pero no le veo sentido a simple vista.
    def envgen_format(self):  # asMultichannelArray, se usa solo en Env y EnvGen.
        if self._envgen_format is None:  # this.array
            self._envgen_format = self._as_array()  # prAsArray
        return self._envgen_format
    def _as_array(self):
        pass  # TODO: prAsArray, si hay variantes hacer dentro de envgen_format.

    ### UGen graph parameter interface ###
    # TODO: ver el resto en UGenParameter

    def as_control_input(self):
        pass # TODO

    ### Node parameter interface ###

    def as_osc_arg_embedded_list(self, lst):
        env_lst = gpp.ugen_param(self).as_control_input()
        return gpp.node_param(env_lst).as_osc_arg_embedded_list(lst)
