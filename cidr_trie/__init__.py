"""cidr_trie

Store CIDR IP addresses (both v4 and v6) in a PATRICIA trie for easy lookup.

Example:
    A Patricia trie can be created, inserted to, and searched like this::
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

        # returns: ['Internet', 'RIR-A', 'another', 'third', 'you']
        trie.find_all("32.32.32.32")
"""

from .cidr_util import is_v6, cidr_atoi, longest_common_prefix_length, get_subnet_mask, ip_itoa
from .bits_util import is_set, ffs
from typing import Any, List


class PatriciaNode:
    """A node in the Patricia trie.

    Attributes:
        ip (int): The IP address associated with this node.
        mask (int): The netmask associated with this node.
        bit (int): How many bits along the IP the decision is made to branch.
        value (Any): The data stored on this node.
        parent (PatriciaNode): The parent of this node.
        left (PatriciaNode): The left subtrie of this node.
        right (PatriciaNode): The right subtrie of this node.
    """
    def __init__(self, ip: int=0, mask: int=0, bit: int=0, data: Any=None) -> None:
        self.ip = ip
        self.mask = mask
        self.bit = bit
        self.value = data
        self.parent = None
        self.left = None
        self.right = None


class PatriciaTrie:
    """A Patricia trie that stores IP addresses and data.

    Attributes:
        root (PatriciaNode): The root element of the trie. Always exists as 0.0.0.0.
        v6 (bool): Whether this trie stores IPv6 addresses or not.
        size (int): The number of nodes in this trie, not counting the root node.

    Example:
        A Patricia trie can be created, inserted to, and searched like this::
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

            # returns: ['Internet', 'RIR-A', 'another', 'third', 'you']
            trie.find_all("32.32.32.32")

    """
    def __init__(self) -> None:
        self.root = PatriciaNode(0, 0, 0)
        self.v6 = False
        self.size = 0

    def insert(self, prefix: str, value: Any) -> None:
        """Insert an IP and value into the trie.

        If the IP was already in the trie it will overwrite the value.

        Args:
            prefix: The prefix to insert, i.e. "192.168.0.0/16"
            value: The value to associate with the IP.

        Example::
            trie = PatriciaTrie()
            trie.insert("192.168.0.0/16", 1234)

        Raises:
            ValueError: When trying to store an IPv4 address in a trie
            currently storing IPv6 addresses, and vice-versa.
        """

        # check to see if the prefix is IPv6 and then check whether
        # or not we can store it given what's already in the trie
        v6 = is_v6(prefix)
        if self.v6 and not v6:
            raise ValueError("Cannot store IPv4 prefix in IPv6 trie")
        elif not self.v6 and v6 and self.size > 0:
            raise ValueError("Cannot store IPv6 prefix in IPv4 trie")
        else:
            self.v6 = v6

        # parse the CIDR string
        ip, mask = cidr_atoi(prefix)

        # traverse with the value until we reach a leaf
        last_node = None
        cur_node = self.root
        while cur_node is not None:
            last_node = cur_node
            if is_set(cur_node.bit, ip, v6):
                cur_node = cur_node.right
            else:
                cur_node = cur_node.left

        # check to see if the last node visited was a match
        if last_node.ip == ip:
            last_node.value = value
            return

        # it wasn't an exact match, so we need to figure out where to
        # insert a new node
        lcp = longest_common_prefix_length(ip, last_node.ip, v6)

        # traverse back up the trie until we find an LCP less than the
        # computed one
        # note: sometimes we don't need to traverse back up, if we reached a
        # leaf with a bit already less than the LCP we can just insert on
        # it and this while loop won't even run
        if cur_node is None:
            cur_node = last_node
        last_node = None
        while cur_node.bit > lcp:
            last_node = cur_node
            cur_node = cur_node.parent

        # we need to find the rightmost set bit of the new IP address
        # to use as the bit of the new node, as any future values of LCP
        # lesser than the position of the rightmost set bit indicate
        # a prefix that is not common to this one
        ip_addr_width = 128 if v6 else 32
        rightmost_set_bit = ip_addr_width - ffs(ip)

        # we've now found a node with a bit lower than the LCP,
        # indicating that it's a valid prefix of the current IP
        # insert the new node on a subtrie of the found node
        to_insert = PatriciaNode(ip, mask, rightmost_set_bit, value)
        to_insert.parent = cur_node
        if is_set(cur_node.bit, ip, v6):
            cur_node.right = to_insert
        else:
            cur_node.left = to_insert

        # if we traversed through another node to get to the
        # found node, we need to put it in a subtrie of the
        # new node
        if last_node is not None:
            last_node.parent = to_insert
            # figure out which subtrie to insert on
            if is_set(to_insert.bit, last_node.ip, v6):
                to_insert.right = last_node
            else:
                to_insert.left = last_node

        # increment the size of the trie due to the added node
        self.size += 1

    def find(self, prefix: str) -> PatriciaNode:
        """Find a value in the trie.

        Args:
            prefix: The prefix to find in the trie, i.e. "192.168.0.0/16"
        
        Returns:
            Any: The data stored in the node if found, None otherwise.

        Raises:
            ValueError: When trying to find an IPv4 address in a v6 trie
            vice-versa.
        """
        v6 = is_v6(prefix)
        if v6 and not self.v6:
            raise ValueError("Trying to find IPv6 value in IPv4 trie")
        elif not v6 and self.v6:
            raise ValueError("Trying to find IPv4 value in IPv6 trie")
        
        ip, _ = cidr_atoi(prefix)
        for node in self.traverse(prefix):
            if node.ip == ip:
                return node

        return None

    def find_all(self, prefix: str) -> List[PatriciaNode]:
        """Traverses the trie and returns any values it found.

        Args:
            prefix: The prefix to find in the trie, i.e. "192.168.0.0/16"

        Returns:
            List[Any]: The values found when traversing the trie.

        Raises:
            ValueError: When trying to find an IPv4 address in a v6 trie
            vice-versa.
        """

        v6 = is_v6(prefix)
        if v6 and not self.v6:
            raise ValueError("Trying to find IPv6 value in IPv4 trie")
        elif not v6 and self.v6:
            raise ValueError("Trying to find IPv4 value in IPv6 trie")

        ip, _ = cidr_atoi(prefix)
        nodes = []
        for node in self.traverse(prefix):
            # if the node's IP fits within the given network, add it to the result
            if node.ip == (ip & get_subnet_mask(node.mask, v6)) and node.value is not None:
                nodes.append(node)

        return nodes

    def traverse(self, prefix: str) -> PatriciaNode:
        """Traverse the trie using a prefix.

        Args:
            prefix: The prefix to find in the trie, i.e. "192.168.0.0/16"

        Yields:
            PatriciaNode: The next node traversed when searching for 'prefix'.

        Raises:
            ValueError: When trying to find an IPv4 address in a v6 trie
            vice-versa.
        """
        v6 = is_v6(prefix)
        if v6 and not self.v6:
            raise ValueError("Trying to find IPv6 value in IPv4 trie")
        elif not v6 and self.v6:
            raise ValueError("Trying to find IPv4 value in IPv6 trie")
        
        ip, _ = cidr_atoi(prefix)

        # look for a leaf
        cur_node = self.root
        while cur_node is not None:
            yield cur_node
            if is_set(cur_node.bit, ip, v6):
                cur_node = cur_node.right
            else:
                cur_node = cur_node.left

    def traverse_inorder(self) -> PatriciaNode:
        """Perform an inorder traversal of the trie.

        Yields:
            PatriciaNode: The next node in the traversal.

        Raises:
            ValueError: When trying to find an IPv4 address in a v6 trie
            vice-versa.
        """
        stack = []
        cur_node = self.root
        while len(stack) > 0 or cur_node is not None:
            while cur_node is not None:
                stack.append(cur_node)
                cur_node = cur_node.left
            
            if len(stack) > 0:
                cur_node = stack.pop()
                yield cur_node
                cur_node = cur_node.right

    def traverse_preorder(self) -> PatriciaNode:
        """Perform a preorder traversal of the trie.

        Yields:
            PatriciaNode: The next node in the traversal.

        Raises:
            ValueError: When trying to find an IPv4 address in a v6 trie
            vice-versa.
        """
        stack = []
        cur_node = self.root
        while len(stack) > 0 or cur_node is not None:
            while cur_node is not None:
                stack.append(cur_node)
                yield cur_node
                cur_node = cur_node.left

            if len(stack) > 0:
                cur_node = stack.pop()
                cur_node = cur_node.right

    def traverse_postorder(self) -> PatriciaNode:
        """Perform a postorder traversal of the trie.

        Yields:
            PatriciaNode: The next node in the traversal.

        Raises:
            ValueError: When trying to find an IPv4 address in a v6 trie
            vice-versa.
        """
        stack = []
        cur_node = self.root
        prev_node = None
        while len(stack) > 0 or cur_node is not None:
            while cur_node is not None:
                stack.append(cur_node)
                cur_node = cur_node.left
            
            while cur_node is None and len(stack) > 0:
                cur_node = stack[-1]
                if cur_node.right is None or cur_node.right == prev_node:
                    yield cur_node
                    stack.pop()
                    prev_node = cur_node
                    cur_node = None
                else:
                    cur_node = cur_node.right
