"""
Variables globales necesarias para la construcción de las SynthDef.
"""

import threading


current_synthdef = None #UGen.buildSynthDef // the synth currently under construction
def_build_lock = threading.Lock()
