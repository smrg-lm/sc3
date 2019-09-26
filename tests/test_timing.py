
from sc3.all import *


# TODO: this are just thrown bits.


# Tolerable math errors.
et = main.elapsed_time()  # or arbitrary numbre from 0.
eoo01 = SystemClock._elapsed_osc_offset
eto = SystemClock.elapsed_time_to_osc(et)
eoo02 = SystemClock._elapsed_osc_offset
ote = SystemClock.osc_to_elapsed_time(eto)
eoo03 = SystemClock._elapsed_osc_offset
if eoo01 == eoo02 == eoo03:  # _elapsed_osc_offset not affected by _resync_thread_func.
    [et, eto, ote, et - ote]  # convertion and rouding error.


# Let's call this 'endogamic clock test'. I think it shows that time between
# thread wakeups is neither constant nor its increments are cumulative which
# defines a numerical behavior for time math. Better tests ideas are welcome.
from sc3.all import *
import sys
import gc
import time
import math

# these options make no real differece.
sys.setswitchinterval(0.000001)  # 0.005 common value
sys.tracebacklimit = 0  # default 1000
gc.disable()

def rout():
    n = 100
    wait_time = 0.1
    maxim = -math.inf
    minim = math.inf
    maxpp = -math.inf
    prev_time = result = avg = 0
    for i in range(n):
        prev_time = time.perf_counter()
        yield wait_time
        result = wait_time - (time.perf_counter() - prev_time)
        maxim = max(maxim, result)
        minim = min(minim, result)
        avg += abs(result)
        if maxim <= 0:
            maxpp = maxim + minim
        else:
            maxpp = maxim - minim
    print(f'max+: {maxim}, max-: {minim}, maxpp: {maxpp}, avg0: {avg/n}')

Routine(rout).play()
