"""Env.sc"""

from sc3.graphparam import UGenParameter, ugen_param,
                                   NodeParameter, node_param


class Env(UGenParameter, NodeParameter):
    # TODO: todo.

    ### UGen graph parameter interface ###
    # TODO: ver el resto en UGenParameter

    def as_control_input(self):
        pass # TODO

    ### Node parameter interface ###

    def as_osc_arg_embedded_list(self, lst):
        env_lst = ugen_param(self).as_control_input()
        return node_para(env_lst).as_osc_arg_embedded_list(lst)
