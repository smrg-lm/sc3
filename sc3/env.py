"""Env.sc"""

from . import graphparam as gpp


class Env(gpp.UGenParameter, gpp.NodeParameter):
    # TODO: todo.

    ### UGen graph parameter interface ###
    # TODO: ver el resto en UGenParameter

    def as_control_input(self):
        pass # TODO

    ### Node parameter interface ###

    def as_osc_arg_embedded_list(self, lst):
        env_lst = gpp.ugen_param(self).as_control_input()
        return gpp.node_param(env_lst).as_osc_arg_embedded_list(lst)
