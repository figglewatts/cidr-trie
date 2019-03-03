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


class RadixTrie:
    root = Node()

    def insert(self, prefix, value):
        cur_bit = 0x80000000  # the MSB of the IP
        cur_node = self.root
        count = 0

        (ip, netmask) = cidrToIpAndNetmask(prefix)

        # while we're within the mask
        while count < netmask:
            val = ip & cur_bit

            # traverse the trie
            if val != 0:
                # right subtrie
                if cur_node.right is None:
                    cur_node.right = Node()
                cur_node = cur_node.right
            else:
                # left subtrie
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


if __name__ == "__main__":
    trie = RadixTrie()
    trie.insert("0.0.0.0/0", 1234)
    trie.insert("192.168.0.1/24", 1235)
    trie.insert("192.168.0.128", 1236)
    print(trie.find("192.168.0.128"))
