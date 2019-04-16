"""bits_util

Contains various utility functions for interacting/manipulating integers
on a bit-level.
"""

def bit_not(n: int, numbits: int=32) -> int:
    """Return the bitwise NOT of 'n' with 'numbits' bits."""
    return (1 << numbits) - 1 - n


def is_set(b: int, val: int, v6: bool) -> bool:
    """Return whether b-th bit is set in integer 'val'."""
    if v6:
        return val & (1 << (127 - b)) != 0
    else:
        return val & (1 << (31 - b)) != 0


def first_set_bit(val: int, v6: bool) -> int:
    """Get the position of the first set bit in integer 'val'."""
    # if b is zero, there is no first set bit
    if val == 0:
        return 0

    # gradually set all bits right of MSB
    max_power_of_2 = 8 if v6 else 5
    n = val | val >> 1
    for i in range(1, max_power_of_2):
        n |= n >> 2**i

    # increment diff by one so that there's only
    # one set bit which is just before original MSB
    n += 1

    # shift it so it's in the original position
    n >>= 1

    # figure out the ordinal of the bit from LSB
    pos = 0
    while (n & 1) == 0:
        n >>= 1
        pos += 1
    return pos
