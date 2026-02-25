"""
main.py

Copyright (c) 2026 Nicolas Mattia

Repository: https://github.com/nmattia/pio-charlie

All rights reserved.
"""

from machine import Pin
import time
import math
import asyncio
import gc

import framebuf
from piocharlie import PIOCharlieBank


# this display is 8 LED wide and 15 LED long.
W = 8
H = 15

# we use 3 charlie buckets/chains, two of 42 LEDs and one of 36 LEDs, abstracted as 3 * 42 bytes.
count = 42  # number of LED per array/display

# in order to cover 42 LEDs we do 7*6 as charlieplexing can drive n_pins * (n_pins - 1) LEDs.
# 8 * 15 = 120, 3 * 42 = 126, with the 6 last "LEDs" of the 3rd array not really existing.
byts = bytearray(3 * 42)  # a bit extra for padding
fbuf = framebuf.FrameBuffer(byts, W, H, framebuf.GS8)

mv = memoryview(byts)  # allows taking slices without copying the buffer


# mark all pins as inputs by default to avoid LEDs leaking
# TODO: why is this necessary when anyway we set pindirs in the PIO?
[Pin(i, Pin.IN, None) for i in range(0, 3 * 7)]

offset_a = 0 * count
charlie_a = PIOCharlieBank(
    mv[offset_a : offset_a + count], sm_ix=0, pin_base=0 * 7, pin_count=7
)

offset_b = 1 * count
charlie_b = PIOCharlieBank(
    mv[offset_b : offset_b + count], sm_ix=1, pin_base=1 * 7, pin_count=7
)

offset_c = 2 * count
charlie_c = PIOCharlieBank(
    mv[offset_c : offset_c + count], sm_ix=2, pin_base=2 * 7, pin_count=7
)

for charlie in [charlie_a, charlie_b, charlie_c]:
    charlie.sm.active(1)  # start the SM
    charlie.dma_looper.active(1)  # start the DMA looper


# little animation
async def pixel_control():
    w = float(W)  # w as in width, not omega
    amp = 0.75 * w  # amplitude
    brit = 64.0
    speed = 5.0  # in pixels per second
    while True:
        delta = -speed * time.ticks_ms() / 1000
        for y in range(0, H):
            # dampen the amplitude at start
            s = (
                amp
                * math.tanh(y / 6.0)
                / 2.0
                * math.sin(2 * math.pi * y / (1.5 * w) + delta)
                + float(W) / 2.0
            )
            for x in range(0, W):
                diff = abs(x - s)
                if diff == 0:
                    v = brit
                else:
                    v = brit / math.exp(1.8 * diff)

                # slow cutoff
                if y >= 8:
                    c = y - 8
                    v *= math.exp(-c / 2.0)

                fbuf.pixel(x, y, int(v))

        gc.collect()
        await asyncio.sleep_ms(16)  # NOTE: should use a ticker instead


asyncio.run(pixel_control())
