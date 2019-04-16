import ipaddress

def bit_not(n, numbits=32):
    return (1 << numbits) - 1 - n

def get_subnet_mask(subnet, v6):
    if v6:
        return bit_not((1 << (128 - subnet)) - 1, 128)
    else:
        return bit_not((1 << (32 - subnet)) - 1, 32)
        #return 0xFFFFFFFF00000000 >> subnet

def is_v6(ip_string):
    return ":" in ip_string

def ip_itoa(ip, v6):
    if v6:
        return str(ipaddress.IPv6Address(ip))
    else:
        return str(ipaddress.IPv4Address(ip))

def ip_atoi(ip_string):
    if is_v6(ip_string):
        return int(ipaddress.IPv6Address(ip_string))
    else:
        return int(ipaddress.IPv4Address(ip_string))

def cidr_atoi(cidr_string):
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
        network = ipaddress.IPv6Network((cidrAndNetmask[0], cidrAndNetmask[1]), False)
    else:
        network = ipaddress.IPv4Network((cidrAndNetmask[0], cidrAndNetmask[1]),
                                        False)
    return (int(network.network_address), network.prefixlen)

def is_set(bit, ip, v6):
    if v6:
        return ip & (1 << (127 - bit)) != 0
    else:
        return ip & (1 << (31 - bit)) != 0

def first_set_bit(b, v6):
    # if b is zero, there is no first set bit
    if b == 0:
        return 0

    # gradually set all bits right of MSB
    max_power_of_2 = 8 if v6 else 5
    n = b | b >> 1
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

def longest_common_prefix_length(a, b, v6):
    return (128 if v6 else 32) - first_set_bit(a ^ b, v6) - 1

class PatriciaNode:
    def __init__(self, ip=0, mask=0, bit=0, data=None):
        self.ip = ip
        self.mask = mask
        self.bit = bit # bit to check
        self.value = data
        self.parent = None
        self.left = None
        self.right = None

class PatriciaTrie:
    def __init__(self):
        self.root = PatriciaNode(0, 0, 0)
        self.v6 = False
        self.size = 0

    def insert(self, prefix, value):
        v6 = is_v6(prefix)
        if self.v6 and not v6:
            raise ValueError("Cannot store IPv4 prefix in IPv6 trie")
        elif not self.v6 and v6 and self.size > 0:
            raise ValueError("Cannot store IPv6 prefix in IPv4 trie")
        else:
            self.v6 = v6
        ip, mask = cidr_atoi(prefix)

        # traverse with the value until we reach a leaf
        last_node = None
        cur_node = self.root
        while cur_node is not None:
            last_node = cur_node
            cur_node = cur_node.right if is_set(cur_node.bit, ip, v6) else cur_node.left

        # check to see if the last node visited was a match
        if last_node.ip == ip:
            last_node.value = value
            return

        # it wasn't an exact match, so we need to figure out where to insert a new node
        lcp = longest_common_prefix_length(ip, last_node.ip, v6)

        # traverse back up the tree until we find an LCP less than the computed one
        # note: sometimes we don't need to traverse back up, if we reached a leaf node
        # with a bit already less than the LCP we can just insert on it and this while
        # loop won't even run
        if cur_node is None:
            cur_node = last_node
        last_node = None
        while cur_node.bit > lcp:
            last_node = cur_node
            cur_node = cur_node.parent

        # we've now found a node with a bit lower than the LCP, 
        # indicating that it's a valid prefix of the current IP
        # insert the new node on a subtree of the found node
        to_insert = PatriciaNode(ip, mask, lcp, value)
        to_insert.parent = cur_node
        if is_set(cur_node.bit, ip, v6):
            cur_node.right = to_insert
        else:
            cur_node.left = to_insert

        # if we traversed through another node to get to the
        # found node, we need to put it in a subtree of the
        # new node
        if last_node is not None:
            last_node.parent = to_insert
            # figure out which subtree to insert on
            if is_set(to_insert.bit, last_node.ip, v6):
                to_insert.right = last_node
            else:
                to_insert.left = last_node

        self.size += 1
        

    def find(self, prefix):
        v6 = is_v6(prefix)
        if v6 and not self.v6:
            raise ValueError("Trying to find IPv6 value in IPv4 trie")
        elif not v6 and self.v6:
            raise ValueError("Trying to find IPv4 value in IPv6 trie")
        ip, _ = cidr_atoi(prefix)
        values = []

        # look for a leaf
        cur_node = self.root
        while cur_node is not None:
            # if it's a valid prefix, add it to results
            if cur_node.ip == (ip & get_subnet_mask(cur_node.mask, v6)):
                values.append(cur_node.value)

            cur_node = cur_node.right if is_set(cur_node.bit, ip, v6) else cur_node.left

        return values

if __name__ == "__main__":
    # supports IPv4
    trie = PatriciaTrie()
    trie.insert("0.0.0.0/0", "Internet")
    trie.insert("32.0.0.0/9", "RIR-A")
    trie.insert("32.128.0.0/9", "RIR-B")
    trie.insert("32.32.0.0/16", "another")
    trie.insert("32.32.32.0/24", "third")
    trie.insert("32.32.32.32/32", "you")
    trie.insert("192.168.0.1/32", "totally different")
    trie.insert("33.0.0.0/8", "RIR3")
    trie.insert("64.0.0.0/8", "RIR2")

    search_for = "32.32.32.32/32"
    print(f"Results for finding {search_for} in IPv4 trie: {trie.find(search_for)}")

    # supports IPv6
    trie = PatriciaTrie()
    trie.insert("::/0", "Internet")
    trie.insert("1234::/16", "Test")
    trie.insert("1234:1001::/32", "Another one")
    trie.insert("1234:1001:1920::/48", "A third")
    trie.insert("1234:1001:1920:2000:2020::/96", "A fourth")
    trie.insert("1234:1001:1920::ffff", "A different one")

    search_for = "1234:1001:1920:2000:2020::/128"
    print(f"Results for finding {search_for} in IPv6 trie: {trie.find(search_for)}")
    search_for = "1234:1001:1920::ffff"
    print(f"Results for finding {search_for} in IPv6 trie: {trie.find(search_for)}")