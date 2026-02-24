# pio-charlie

Proof of concept for driving LEDs from the rp2040's PIO.

The LEDs are charlieplexed, meaning N pins can drive N (N-1) LEDs, or e.g. 11 pins can drive 110 LEDs. The charlieplexing patterns are generated directly from the PIO, meaning the CPUs can idle. For one group of LEDs, one PIO SM and two DMA channels are necessary. This example shown below uses 3 groups of 42 LEDs.

This wiring means only one LED is on at any time, and unless the displayed data has to be updated, the CPUs can WFI. This means little current usage, or alternatively much better performance as the cores are free to perform other tasks, without the need for extra silicon.

Brightness control is supported and the "on" time is shared across all the LEDs, meaning this is ideal for low brightness applications or applications where only a few pixels need to be on at a time.
