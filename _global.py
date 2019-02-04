"""
Variables globales necesarias para la construcción de las SynthDef.
"""

import threading

main_thread = None
this_thread = None

current_synthdef = None # UGen.buildSynthDef // the synth currently under construction
def_build_lock = threading.Lock()
