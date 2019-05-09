"""
Contains various utility functions for interacting/manipulating IP and CIDR
addresses.
"""

import ipaddress
from typing import Tuple
from .bits_util import bit_not, fls


def get_subnet_mask(subnet: int, v6: bool) -> int:
    """Get the subnet mask given a CIDR prefix 'subnet'."""
    if v6:
        return bit_not((1 << (128 - subnet)) - 1, 128)
    else:
        return bit_not((1 << (32 - subnet)) - 1, 32)


def is_v6(ip_string: str) -> bool:
    """Returns True if a given IP string is v6, False otherwise."""
    return ":" in ip_string


def ip_itoa(ip: int, v6: bool) -> str:
    """Converts an IP integer 'ip' to a string."""
    if v6:
        return str(ipaddress.IPv6Address(ip))
    else:
        return str(ipaddress.IPv4Address(ip))


def ip_atoi(ip_string: str) -> int:
    """Converts an IP string 'ip_string' to an integer."""
    if is_v6(ip_string):
        return int(ipaddress.IPv6Address(ip_string))
    else:
        return int(ipaddress.IPv4Address(ip_string))


def cidr_atoi(cidr_string: str) -> Tuple[int, int]:
    """Convert a CIDR string to a network and prefix length tuple.
    Supports IPv4 and IPv6.

    Args:
        cidr_string: The CIDR as a string, i.e. "192.168.0.0/16"
    Returns:
        A tuple containing the integer IP address of the network (the lowest IP inside)
        and the prefix length. i.e. (int(192.168.0.0), 16) for "192.168.0.0/16".
    """
    cidrAndNetmask = cidr_string.split("/")

    v6 = is_v6(cidrAndNetmask[0])

    # check to see if a CIDR netmask was supplied, and return
    # just the IP if not
    if len(cidrAndNetmask) < 2:
        if v6:
            return (int(ipaddress.IPv6Address(cidrAndNetmask[0])), 128)
        else:
            return (int(ipaddress.IPv4Address(cidrAndNetmask[0])), 32)

    network = None
    if v6:
        network = ipaddress.IPv6Network((cidrAndNetmask[0], cidrAndNetmask[1]),
                                        False)
    else:
        network = ipaddress.IPv4Network((cidrAndNetmask[0], cidrAndNetmask[1]),
                                        False)
    return (int(network.network_address), network.prefixlen)


def longest_common_prefix_length(a: int, b: int, v6: bool) -> int:
    """Find the longest common prefix length of 'a' and 'b'."""
    return (128 if v6 else 32) - fls(a ^ b, v6) - 1
