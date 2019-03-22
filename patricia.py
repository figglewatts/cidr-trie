import ipaddress

def get_subnet_mask(subnet):
    # TODO: change for IPv6?
    return (0xFFFFFFFF00000000 >> subnet) & 0xFFFFFFFF


def ip_atoi(ipString):
    return int(ipaddress.IPv4Address(ipString))


def cidr_atoi(cidrString):
    cidrAndNetmask = cidrString.split("/")

    # check to see if a CIDR netmask was supplied, and return
    # just the IP if not
    if len(cidrAndNetmask) < 2:
        # TODO: change for IPv6
        return (int(ipaddress.IPv4Address(cidrAndNetmask[0])), 32)

    network = ipaddress.IPv4Network((cidrAndNetmask[0], cidrAndNetmask[1]),
                                    False)
    return (int(network.network_address), network.prefixlen)

def is_set(bit, ip):
    return ip & (1 << (31 - bit)) != 0

def first_set_bit(b):
    # if b is zero, there is no first set bit
    if b == 0:
        return -1

    # TODO: change for 128 bits of IPv6
    # gradually set all bits right of MSB
    n = b | b >> 1
    n |= n >> 2
    n |= n >> 4
    n |= n >> 8
    n |= n >> 16

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

def longest_common_prefix_length(a, b):
    return 32 - first_set_bit(a ^ b) - 1

class Node:
    def __init__(self, ip=0, mask=0, bit=0, data=None):
        self.ip = ip
        self.mask = mask
        self.bit = bit # bit to check
        self.data = data
        self.parent = None
        self.left = None
        self.right = None


class PatriciaTrie:
    root = None

    def insert(self, prefix, value):
        ip, netmask = cidr_atoi(prefix)

        to_insert = Node(ip, netmask, 0, value)
        if self.root is None:
            self.root = to_insert
            return

        # look for a leaf
        last_node = None
        cur_node = self.root
        while cur_node is not None:
            last_node = cur_node
            cur_node = cur_node.right if is_set(cur_node.bit, ip) else cur_node.left

        # check to see if it's an exact match
        if last_node.ip == ip:
            last_node.value = value
            return

        # find the longest common prefix
        lcp = longest_common_prefix_length(last_node.ip, ip)

        # go back up the tree to find a less specific prefix if
        # the leaf is more specific than we need
        while lcp < last_node.bit:
            print("going up...")
            last_node = last_node.parent

        to_insert.bit = lcp
        to_insert.parent = last_node
        if is_set(last_node.bit, to_insert.ip):
            print("inserting right")
            if last_node.right is not None:
                last_node.right.parent = to_insert
            to_insert.right = last_node.right
            last_node.right = to_insert
        else:
            print("inserting left")
            if last_node.left is not None:
                last_node.left.parent = to_insert
            to_insert.left = last_node.left
            last_node.left = to_insert

    def find(self, prefix):
        ip, _ = cidr_atoi(prefix)
        values = []

        # look for a leaf
        cur_node = self.root
        while cur_node is not None:
            # if it's a valid prefix, add it to results
            if cur_node.ip == (ip & get_subnet_mask(cur_node.mask)):
                values.append(cur_node.data)

            cur_node = cur_node.right if is_set(cur_node.bit, ip) else cur_node.left

        return values

if __name__ == "__main__":
    trie = PatriciaTrie()
    trie.insert("0.0.0.0/0", "internet")
    trie.insert("32.0.0.0/8", "RIR")
    trie.insert("32.32.0.0/16", "another")
    trie.insert("32.32.32.0/24", "third")
    trie.insert("33.0.0.0/8", "RIR3")
    trie.insert("64.0.0.0/8", "RIR2")

    print(trie.find("32.32.0.0/16"))