"""
main.py

Copyright (c) 2026 Nicolas Mattia

Repository: https://github.com/nmattia/pio-charlie

All rights reserved.
"""

from machine import Pin
import time
import math

from piocharlie import PIOCharlieBank

# mark all pins as inputs by default to avoid LEDs leaking
for i in range(0, 16):
    _ = Pin(i, Pin.IN, None)

# create two bytearrays with corresponding PIO banks, one for each LED color

wheels = bytearray(8 * 7)
charlie_wheels = PIOCharlieBank(wheels, sm_ix=0, pin_base=0, pin_count=8)
charlie_wheels.sm.active(1)
charlie_wheels.dma_looper.active(1)

frame = bytearray(8 * 7)
charlie_frame = PIOCharlieBank(frame, sm_ix=1, pin_base=8, pin_count=8)
charlie_frame.sm.active(1)
charlie_frame.dma_looper.active(1)

# the wheels & hub are animated separately, so split them up with memory views for simplicity
wheels_mv = memoryview(wheels)
wheels_back = wheels_mv[0:20]
wheels_hub = wheels_mv[20 : 20 + 9]
wheels_front = wheels_mv[29 : 29 + 25]

# set up the (static) frame lighting
for ix in range(0, 4):  # saddle
    frame[ix] = 255

for ix in range(4, 20):  # seat post
    frame[ix] = 16

for ix in range(20, 36):  # rest of the frame
    frame[ix] = 64

for ix in range(36, 54):  # handlebars
    frame[ix] = 255

# forever animate the wheels
while True:
    t = time.ticks_ms() / 1000.0

    # for each wheel and for the hub, we iterate through the LEDs, compute the angular position
    # of the LED in the wheel/hub, and compute the intensity at said position.

    for ix, _ in enumerate(wheels_front):
        theta = (
            math.tau * float(ix) / float(len(wheels_front))
        )  # LED position in the wheel
        f = 0.5  # RPS
        wheels_front[ix] = max(1, int(16.0 * math.sin(math.tau * f * t + theta)))

    for ix, _ in enumerate(wheels_back):
        # LED position in the wheel
        # NOTE: the back wheel has ~10 LEDs fewer than the front wheel so we compensate
        # NOTE: we shift this wheel's animation by PI so that both wheels are slightly out of phase
        theta = math.tau * float(ix) / float(len(wheels_back) + 10) - math.pi
        f = 0.5  # RPS
        wheels_back[ix] = max(1, int(16.0 * math.sin(math.tau * f * t + theta)))

    for ix, _ in enumerate(wheels_hub):
        theta = (
            math.tau * float(ix) / float(len(wheels_hub))
        )  # LED position in the wheel
        f = 0.1  # slightly slower RPS than the wheels
        wheels_hub[ix] = max(1, int(16.0 * math.sin(math.tau * f * t + theta)))
