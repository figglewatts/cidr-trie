"""
Contains various utility functions for interacting/manipulating integers
on a bit-level.
"""

def bit_not(n: int, numbits: int=32) -> int:
    """Return the bitwise NOT of 'n' with 'numbits' bits."""
    return (1 << numbits) - 1 - n


def is_set(b: int, val: int, v6: bool) -> bool:
    """Return whether b-th bit is set in integer 'val'.
    
    Special case: when b < 0, it acts as if it were 0.
    """
    if b < 0:
        b = 0

    if v6:
        return val & (1 << (127 - b)) != 0
    else:
        return val & (1 << (31 - b)) != 0


def fls(val: int, v6: bool) -> int:
    """Find last set - returns the index, counting from 0 (from the right) of the
    most significant set bit in `val`."""
    # if b is zero, there is no first set bit
    if val == 0:
        return 0

    # gradually set all bits right of MSB
    # this technique is called 'bit smearing'
    # if ipv6, max bit index we want to smear is 2^7=64, 
    # otherwise it's 2^4=16
    max_power_of_2 = 7 if v6 else 5
    n = val | val >> 1
    for i in range(1, max_power_of_2+1):
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


def ffs(x: int) -> int:
    """Find first set - returns the index, counting from 0 (from the right), of the
    least significant set bit in `x`.
    """
    return (x&-x).bit_length()-1
