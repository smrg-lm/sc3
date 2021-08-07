
from sc3.all import *


# TODO: this are just thrown bits.

########################
# Tolerable math errors.
et = main.elapsed_time()  # or arbitrary numbre from 0.
eoo01 = SystemClock._elapsed_osc_offset
eto = SystemClock.elapsed_time_to_osc(et)
eoo02 = SystemClock._elapsed_osc_offset
ote = SystemClock.osc_to_elapsed_time(eto)
eoo03 = SystemClock._elapsed_osc_offset
if eoo01 == eoo02 == eoo03:  # assert
    [et, eto, ote, et - ote]  # conversion and rouding error.


t1 = main.current_tt.seconds
o1 = SystemClock.elapsed_time_to_osc(t1)
t2 = SystemClock.osc_to_elapsed_time(o1)
[t1, t2, t1 - t2] # t1 - t2 > 0 retrieved time is in the past at picoseconds without _sync_osc_offset_with_tod.


############################################################################
# Let's call this 'endogamic clock test'. I think it shows that time between
# thread wakeups is neither constant nor its increments are cumulative which
# defines a numerical behavior for time math. Better tests ideas are welcome.
from sc3.all import *
import sys
import gc
import time

# these options make no real differece.
sys.setswitchinterval(0.000001)  # 0.005 common value
sys.tracebacklimit = 0  # default 1000
gc.disable()

def rout():
    n = 100
    wait_time = 0.1
    maxim = float('-inf')
    minim = float('inf')
    maxpp = float('-inf')
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


##################################
# Logical time == bundle time test
# TODO: check all possible calls to _update_logical_time, make a map.
# TODO: trace and profile all logical time updates.
from sc3.all import *

n = NetAddr('127.0.0.1', NetAddr.lang_port())
time_steps = []

def recv_func(*args):
    time_steps.append(args[1])

recv = OscFunc(recv_func, '/test')

@routine
def ro():
    for i in range(3):
        time_steps.append(main.current_tt.seconds)  # must be almost the same time of the bundle (floating point error)
        n.send_bundle(0, ['/test'])
        yield 1
    print([round(time_steps[i], 9) == round(time_steps[i + 1], 9)\
           for i in range(0, len(time_steps), 2)])  # equal at nanos.

ro.play()
# [round(time_steps[i], 9) == round(time_steps[i + 1], 9) for i in range(0, len(time_steps), 2)]
# recv.free()
