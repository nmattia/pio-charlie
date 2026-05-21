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


W = 6
H = 5

count = 30  # number of LED per array/display

byts = bytearray(30)  # a bit extra for padding
fbuf = framebuf.FrameBuffer(byts, W, H, framebuf.GS8)

mv = memoryview(byts)  # allows taking slices without copying the buffer

# mark all pins as inputs by default to avoid LEDs leaking
# TODO: why is this necessary when anyway we set pindirs in the PIO?
[Pin(i, Pin.IN, None) for i in range(0, 6)]

charlie = PIOCharlieBank(mv[0:count], sm_ix=0, pin_base=0, pin_count=6)

charlie.sm.active(1)  # start the SM
charlie.dma_looper.active(1)  # start the DMA looper


# little animation
async def pixel_control():
    while True:
        for y in range(0, H):
            for x in range(0, W):
                v = 0
                while v < 200:
                    fbuf.pixel(x, y, v)
                    await asyncio.sleep_ms(16)
                    v += 3

                v = 200

                while v > 0:
                    fbuf.pixel(x, y, v)
                    await asyncio.sleep_ms(16)
                    v -= 2

                v = 0
                fbuf.pixel(x, y, v)

        gc.collect()


asyncio.run(pixel_control())
