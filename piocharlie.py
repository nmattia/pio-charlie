"""
piocharlie.py

Copyright (c) 2026 Nicolas Mattia

Repository: https://github.com/nmattia/pio-charlie

All rights reserved.
"""

import array
import rp2
from uctypes import addressof


class PIOCharlieBank:
    # rp2.StateMachine can reuse the program in the PIO bank memory iff the "program" (as seen by MicroPython)
    # is ref-equal, so we memoize the program by pin_count
    by_pins = {}

    def pio_prog(pin_count):

        res = PIOCharlieBank.by_pins.get(pin_count)
        if res:
            return res

        # NOTE: cannot autopull bc `mov(dest, OSR)` is then undefined
        @rp2.asm_pio(
            out_init=(rp2.PIO.OUT_LOW,) * pin_count,
            out_shiftdir=rp2.PIO.SHIFT_RIGHT,
            in_shiftdir=rp2.PIO.SHIFT_LEFT,
        )
        def pio_charlie(
            n_pins=pin_count,
        ):  # hack to make pin_count accessible in definition
            # ruff: disable[F821]
            y_zero = not_y

            label("top")
            # set ISR to 0b..._XX10001
            set(y, 0b1)
            in_(y, 1)
            in_(y, n_pins - 1)

            # here we expect ISR to contain the next pattern to flash, or rather the least significant
            # 'n_pins bit group (more significant bits do not matter and can be set arbitrarily).
            wrap_target()
            mov(osr, isr)
            out(pindirs, n_pins)  # cannot 'mov' here (no support for mov pindirs)

            mov(x, isr)  # here we save the pattern into X for later use
            mov(isr, invert(null))  # here ISR is 111...111

            # here we create the pattern that'll be used to set pin values.
            # After this, the ISR's least significant bits will be zeros, starting with the bit position
            # of the pattern's least significant '1':
            #           . .
            #  X  = 00001010
            #             |
            # ISR = 11111100
            #           H L
            #
            # This ensures that ISR will set one bit HIGH and one bit LOW (only the values set to 1 with
            # pindirs matter).
            mov(osr, x)
            label(
                "more"
            )  # load ISR with zeros from the right as long as the LSB of OSR is 0
            out(y, 1)
            in_(null, 1)  # 111...111 -> 111...110, then 111...110 -> 111...100, etc
            jmp(y_zero, "more")

            # pull a 4-byte value from the queue and pad the most significant 'sig_bits' bits
            # to the right of Y. Only the most significant 8 bits in the OSR matter because
            # of lane replication.
            sig_bits = 8  # least significant byte of the OSR

            label("loop")

            pull()  # we cannot autopull bc we don't know the OSR bitcount after the "more" loop above
            out(y, sig_bits)  # Y is 000...<least significant bits that were pulled>
            # if it's zero, shortcut everything to avoid light flashing/ghosting
            jmp(y_zero, "wait")
            mov(pins, isr)
            label("wait")
            jmp(y_dec, "wait")

            # ensures pins are all shut off as soon as possible to prevent ghosting
            mov(pins, null)

            mov(osr, isr)
            out(y, 1)  # here y == 0 for the first loop and y == 1 for the second loop
            mov(isr, invert(isr))
            jmp(y_zero, "loop")

            # at this point y == 1

            mov(osr, x)  # STOP

            out(y, 1)
            jmp(y_zero, "save_and_flash")  # we've output a zero, branch out

            # here y is 000...001 if LSB of OSR is 1, 000...000 otherwise
            out(y, 1)
            jmp(y_dec, "top")  # output 1 & 1: take it from the top

            # here y is 111...111 (bc y_dec did not trigger meaning Y was 0; then post dec made it wrap around)

            out(isr, 32)  # avoid mov(dest, OSR) not working with autopull
            in_(
                y, 1
            )  # 1 & 0: now total action was: ...0101 -> ...0010 -> ..0001 -> ... 0011

            # now we reverse the least significant 'n_pins' bits
            # (in other words, pad the pattern to the left)
            #
            # 000...0100001 -> 01000010...000 -> 000...1000010
            # ......<_____<    <_____<                 >_____>
            #
            in_(null, 32 - n_pins)
            mov(osr, reverse(isr))

            label("save_and_flash")
            out(isr, 32)  # avoid mov(dest, OSR) not working with autopull

            nop()  # with room to spare!
            # ruff: enable[F821]

        PIOCharlieBank.by_pins[pin_count] = pio_charlie
        return pio_charlie

    def __init__(
        self,
        buf,
        pin_base=0,
        pin_count=1,
        sm_ix=0,
        freq=1_000_000,
    ):
        self.sm = rp2.StateMachine(
            sm_ix, PIOCharlieBank.pio_prog(pin_count), freq=freq, out_base=pin_base
        )

        # NOTE: self.dma and self.arr _cannot_ move
        # TODO: pin them?
        self.dma = rp2.DMA()
        self.dma_looper = rp2.DMA()

        self.arr = array.array("I")
        # TODO: add support for double buffering
        self.arr.append(addressof(buf))

        self.dma.config(
            write=self.sm,
            count=len(buf),
            ctrl=self.dma.pack_ctrl(
                size=0,
                inc_write=False,
                inc_read=True,
                treq_sel=sm_ix,  # DREQ_PIO0_TX0 + ix, see [rp2040 datasheet, 2.5.3.1. System DREQ Table]
                chain_to=self.dma_looper.channel,  # trigger looper when done, see below
            ),
        )

        # the "DMA looper"'s job is to restart the DMA transfer by resetting the "read" address
        # to that of the start of the buf. The address is written to the DMA's READ_ADDR_TRIG
        # (in the datasheet: READ_ADD_TRIG) which (1) (re)sets the read address and (2) triggers
        # the DMA to re-run.
        # see triggers, [rp2040 datasheet, 2.5.2.1. Aliases and Triggers]
        self.dma_looper.config(
            read=self.arr,
            write=self.dma.registers[15:],
            count=1,
            ctrl=self.dma_looper.pack_ctrl(
                inc_write=False,
                inc_read=False,
            ),
        )
