import ipaddress

def get_subnet_mask(subnet):
    # TODO: change for IPv6?
    return (0xFFFFFFFF00000000 >> subnet) & 0xFFFFFFFF

def ip_itoa(ip):
    return str(ipaddress.IPv4Address(ip))

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
        return 0

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

    def insert(self, prefix, value):
        ip, mask = cidr_atoi(prefix)

        # traverse with the value until we reach a leaf
        last_node = None
        cur_node = self.root
        while cur_node is not None:
            last_node = cur_node
            cur_node = cur_node.right if is_set(cur_node.bit, ip) else cur_node.left

        # check to see if the last node visited was a match
        if last_node.ip == ip:
            last_node.value = value
            return

        # it wasn't an exact match, so we need to figure out where to insert a new node
        lcp = longest_common_prefix_length(ip, last_node.ip)

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
        if is_set(cur_node.bit, ip):
            cur_node.right = to_insert
        else:
            cur_node.left = to_insert

        # if we traversed through another node to get to the
        # found node, we need to put it in a subtree of the
        # new node
        if last_node is not None:
            last_node.parent = to_insert
            # figure out which subtree to insert on
            if is_set(to_insert.bit, last_node.ip):
                to_insert.right = last_node
            else:
                to_insert.left = last_node
        

    def find(self, prefix):
        ip, _ = cidr_atoi(prefix)
        values = []

        # look for a leaf
        cur_node = self.root
        while cur_node is not None:
            # if it's a valid prefix, add it to results
            if cur_node.ip == (ip & get_subnet_mask(cur_node.mask)):
                values.append(cur_node.value)

            cur_node = cur_node.right if is_set(cur_node.bit, ip) else cur_node.left

        return values

if __name__ == "__main__":
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

    print(trie.find("192.168.0.1/32"))