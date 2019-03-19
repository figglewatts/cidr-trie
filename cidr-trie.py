import ipaddress


def getSubnetMask(subnet):
    # TODO: change for IPv6?
    return (0xFFFFFFFF00000000 >> subnet) & 0xFFFFFFFF


def ipStringToInt(ipString):
    return int(ipaddress.IPv4Address(ipString))


def cidrToIpAndNetmask(cidrString):
    cidrAndNetmask = cidrString.split("/")

    # check to see if a CIDR netmask was supplied, and return
    # just the IP if not
    if len(cidrAndNetmask) < 2:
        # TODO: change for IPv6
        return (int(ipaddress.IPv4Address(cidrAndNetmask[0])), 32)

    network = ipaddress.IPv4Network((cidrAndNetmask[0], cidrAndNetmask[1]),
                                    False)
    return (int(network.network_address), network.prefixlen)


class Node:
    left = None
    right = None
    value = None


class BinaryTree:
    root = Node()

    def insert(self, prefix, value):
        cur_bit = 0x80000000  # the MSB of the IP
        cur_node = self.root
        count = 0

        (ip, netmask) = cidrToIpAndNetmask(prefix)

        # while we're within the mask
        while count < netmask:
            val = ip & cur_bit

            # traverse the tree
            if val != 0:
                # right subtree
                if cur_node.right is None:
                    cur_node.right = Node()
                cur_node = cur_node.right
            else:
                # left subtree
                if cur_node.left is None:
                    cur_node.left = Node()
                cur_node = cur_node.left

            count += 1
            cur_bit >>= 1

        cur_node.value = value
        print("Inserted at level {}".format(count))

    def find(self, prefix):
        cur_bit = 0x80000000  # the MSB of the IP
        cur_node = self.root
        values = []

        (ip, netmask) = cidrToIpAndNetmask(prefix)

        while cur_node is not None:
            if cur_node.value is not None:
                values.append(cur_node.value)

            val = ip & cur_bit
            if val != 0:
                cur_node = cur_node.right
            else:
                cur_node = cur_node.left

            cur_bit >>= 1

        return values

def first_set_bit(b):
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

def longest_common_prefix(a, b):
    diff = a ^ b # binary difference
    first_bit = first_set_bit(diff)
    return a >> (first_bit + 1)
    

class PatriciaNode:
    left = None
    right = None
    skip = None
    ip = 0
    value = None

class PatriciaTrie:
    root = None

    def insert(self, prefix, value):
        cur_bit = 0x80000000  # the MSB of the IP
        cur_node = self.root
        cur_skip = 0

        (ip, netmask) = cidrToIpAndNetmask(prefix)

        if cur_node is None:
            cur_node = PatriciaNode()

        # while we're within the mask
        while cur_skip < netmask:
            # insert if we get to a null node
            if cur_node is None:
                break
            
            lcp_len = longest_common_prefix_length(cur_node.ip, ip)
            cur_bit >>= lcp_len
            cur_skip += lcp_len
            val = ip & cur_bit

            # traverse the trie
            if val != 0:
                # right subtrie
                print("right")
                if cur_node.right is None:
                    cur_node.right = Node()
                cur_node = cur_node.right
            else:
                # left subtrie
                print("left")
                if cur_node.left is None:
                    cur_node.left = Node()
                cur_node = cur_node.left

            cur_skip += 1
            cur_bit >>= 1

        cur_node.value = value
        cur_node.skip = cur_skip
        cur_node.ip = ip
        print("Inserted with skip {}".format(cur_skip))

if __name__ == "__main__":
    #tree = BinaryTree()
    #tree.insert("0.0.0.0/0", 1234)
    #tree.insert("192.168.0.1/24", 1235)
    #tree.insert("192.168.0.128", 1236)
    #print(tree.find("192.168.0.128"))

    trie = PatriciaTrie()
    trie.insert("0.0.0.0/0", 1234)
    trie.insert("128.0.0.0/1", 1235)

    """ a = 0xF0F0FFFF
    b = 0xF0F0FAFF
    print(f"{a:b}")
    print(f"{b:b}")
    lcp = longest_common_prefix(a, b)
    print(f"{lcp:b}")
    l = longest_common_prefix_length(a, b)
    print(l)
    r = 0x80000000 >> l
    print(f"{r:32b}") """
