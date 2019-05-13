"""Store CIDR IP addresses (both v4 and v6) in a PATRICIA trie for easy lookup.

A Patricia trie can be created, inserted to, and searched like this

.. code-block:: python

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

    # a generator for nodes corresponding to: ['Internet', 'RIR-A', 'another', 'third', 'you']
    trie.find_all("32.32.32.32")
"""

from .cidr_util import is_v6, cidr_atoi, longest_common_prefix_length, get_subnet_mask, ip_itoa
from .bits_util import is_set, ffs
from typing import Any, List, Dict, Tuple


class PatriciaNode:
    """A node in the Patricia trie.

    Attributes:
        ip (int): The IP address associated with this node.
        bit (int): How many bits along the IP the decision is made to branch.
        value (Dict[int, Any]): The data stored on this node. Maps netmasks to data.
        parent (PatriciaNode): The parent of this node.
        left (PatriciaNode): The left subtrie of this node.
        right (PatriciaNode): The right subtrie of this node.
    """
    def __init__(self, ip: int=0, bit: int=0, data: Dict[int, Any]={}) -> None:
        self.ip = ip
        self.bit = bit
        self.value = data
        self.parent = None
        self.left = None
        self.right = None

    def get_values(self, prefix: str) -> Dict[str, Any]:
        """Get values from this node by iterating through netmasks and
        checking to see if the given prefix is contained within.

        Args:
            prefix: The prefix to use to check, i.e. "192.168.0.0/16"
        Returns:
            Dict[str, Any]: dict mapping prefixes to values, i.e. {"192.168.0.0/16": 2856}
        """
        # parse the CIDR string
        ip, mask = cidr_atoi(prefix)
        v6 = is_v6(prefix)
        result = {}

        # for each mask stored in this node, check to see if the IP given
        # by the prefix masked by the mask is equal to the IP stored in the node
        # this indicates that this IP is within the network defined by the node
        # IP and particular netmask
        for m in self.value.keys():
            # if the mask is greater than the given mask, there's no way the prefix
            # can be in this range, as it's bigger than this network
            if m > mask:
                continue

            if self.ip == (ip & get_subnet_mask(m, v6)):
                result[f"{ip_itoa(self.ip, False)}/{m}"] = self.value[m]

        return result


class PatriciaTrie:
    """A Patricia trie that stores IP addresses and data.

    Attributes:
        root (PatriciaNode): The root element of the trie. Always exists as 0.0.0.0.
        v6 (bool): Whether this trie stores IPv6 addresses or not.
        size (int): The number of nodes in this trie, not counting the root node.

    A Patricia trie can be created, inserted to, and searched like this

    .. code-block:: python

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

        # a generator for nodes corresponding to: ['Internet', 'RIR-A', 'another', 'third', 'you']
        trie.find_all("32.32.32.32")

    """
    def __init__(self) -> None:
        self.root = PatriciaNode(0, 0)
        self.v6 = False
        self.size = 0

    def insert(self, prefix: str, data: Any) -> PatriciaNode:
        """Insert an IP and data into the trie.

        If the IP was already in the trie it will overwrite the value.

        .. code-block:: python

            trie = PatriciaTrie()
            trie.insert("192.168.0.0/16", 1234)

        Args:
            prefix: The prefix to insert, i.e. "192.168.0.0/16"
            data: The value to associate with the IP and netmask.

        Returns:
            PatriciaNode: The node that was inserted in the trie.

        Raises:
            ValueError: When trying to store an IPv4 address in a trie currently storing IPv6 addresses, and vice-versa.
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
            # if it was, set the value and return the node
            last_node.value[mask] = data
            return last_node

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
        rightmost_set_bit = ip_addr_width - ffs(ip) - 1

        # we've now found a node with a bit lower than the LCP,
        # indicating that it's a valid prefix of the current IP
        # insert the new node on a subtrie of the found node
        to_insert = PatriciaNode(ip, rightmost_set_bit, {mask: data})
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

        # return the inserted node
        return to_insert

    def check_value_exists(self, prefix: str) -> (bool, bool):
        """Check to see if a value exists in the trie already.
        Returns 2 bools, the first to indicate whether the IP existed in the trie, and the
        second to indicate whether the mask existed on that IP.

        There can only be one of any IP stored in the trie, if you stored 2 prefixes,
        "192.168.0.0/16", and "192.168.0.0/24", the data would be stored on the same
        node, as the IP address "192.168.0.0" is the same. Even though these refer
        to 2 separate networks.
        
        This method exists so you can check to see if this will happen. The first boolean
        returned indicates if an IP address is already present, for example in the case
        above, if called after inserting "192.168.0.0/16", this method would return True
        in the first boolean for a prefix of "192.168.0.0/24" and other netmasks, and False
        for the second boolean.
        The second boolean is for checking if the mask is present -- if called after
        inserting "192.168.0.0/16" with a prefix of "192.168.0.0/16" it would return
        True for both booleans.

        Args:
            prefix: The prefix to find in the trie, i.e. "192.168.0.0/16"

        Returns:
            (bool, bool): A 2-tuple of bools indicating whether the IP existed and the mask existed, respectively.

        Raises:
            ValueError: When trying to find an IPv4 address in a v6 trie and vice-versa.
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

        # traverse the trie with the given IP
        last_node = None
        for node in self.traverse(prefix):
            last_node = node

        ip_exists = False
        mask_exists = False

        if last_node.ip == ip:
            # if the last node's IP equals this IP, the IP exists
            # we now need to check if the mask is in the set of masks
            ip_exists = True
            mask_exists = mask in last_node.value
        else:
            # if the IP didn't exist, we can be sure the mask didn't either
            ip_exists = False
            mask_exists = False

        return ip_exists, mask_exists

    def find(self, prefix: str) -> PatriciaNode:
        """Find a value in the trie.

        Args:
            prefix: The prefix to find in the trie, i.e. "192.168.0.0/16"
        
        Returns:
            PatriciaNode: The node if found, None otherwise.

        Raises:
            ValueError: When trying to find an IPv4 address in a v6 trie and vice-versa.
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

    def find_all_values(self, prefix: str) -> Dict[str, Any]:
        v6 = is_v6(prefix)
        if v6 and not self.v6:
            raise ValueError("Trying to find IPv6 value in IPv4 trie")
        elif not v6 and self.v6:
            raise ValueError("Trying to find IPv4 value in IPv6 trie")

        values = {}

        # for each node on the way down
        for node in self.traverse(prefix):
            # get the values from the node and combine them into
            # the result dictionary
            vals = node.get_values(prefix)
            values = {**values, **vals}
        return values


    def find_all(self, prefix: str) -> List[PatriciaNode]:
        """Traverses the trie and returns any nodes it found.

        Args:
            prefix: The prefix to find in the trie, i.e. "192.168.0.0/16"

        Returns:
            List[PatriciaNode]: Ordered list of nodes found when traversing the trie.

        Raises:
            ValueError: When trying to find an IPv4 address in a v6 trie and vice-versa.
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
        """Traverse the entire trie (from root) using a prefix.

        Args:
            prefix: The prefix to find in the trie, i.e. "192.168.0.0/16"

        Yields:
            PatriciaNode: The next node traversed when searching for 'prefix'.

        Raises:
            ValueError: When trying to find an IPv4 address in a v6 trie and vice-versa.
        """
        for node in self.traverse_from_node(self.root, prefix):
            yield node

    def traverse_from_node(self, node: PatriciaNode, prefix: str) -> PatriciaNode:
        """Traverse the trie from a specific node using a prefix.

        Args:
            node: The node to start traversing from.
            prefix: The prefix to find in the trie, i.e. "192.168.0.0/16"

        Yields:
            PatriciaNode: The next node traversed when searching for 'prefix'.

        Raises:
            ValueError: When trying to find an IPv4 address in a v6 trie and vice-versa.

        """
        v6 = is_v6(prefix)
        if v6 and not self.v6:
            raise ValueError("Trying to find IPv6 value in IPv4 trie")
        elif not v6 and self.v6:
            raise ValueError("Trying to find IPv4 value in IPv6 trie")
        
        ip, _ = cidr_atoi(prefix)

        # look for a leaf
        cur_node = node
        while cur_node is not None:
            yield cur_node
            if is_set(cur_node.bit, ip, v6):
                cur_node = cur_node.right
            else:
                cur_node = cur_node.left

    def traverse_inorder(self) -> PatriciaNode:
        """Perform an inorder traversal of the trie from the root node.

        Yields:
            PatriciaNode: The next node in the traversal.

        Raises:
            ValueError: When trying to find an IPv4 address in a v6 trie and vice-versa.
        """
        for node in self.traverse_inorder_from_node(self.root):
            yield node

    def traverse_inorder_from_node(self, node: PatriciaNode) -> PatriciaNode:
        """Perform an inorder traversal of the trie from a given node.

        Args:
            node: The node to traverse from.

        Yields:
            PatriciaNode: The next node in the traversal.

        Raises:
            ValueError: When trying to find an IPv4 address in a v6 trie and vice-versa.
        """
        stack = []
        cur_node = node
        while len(stack) > 0 or cur_node is not None:
            while cur_node is not None:
                stack.append(cur_node)
                cur_node = cur_node.left
            
            if len(stack) > 0:
                cur_node = stack.pop()
                yield cur_node
                cur_node = cur_node.right

    def traverse_preorder(self) -> PatriciaNode:
        """Perform a preorder traversal of the trie from the root node.

        Yields:
            PatriciaNode: The next node in the traversal.

        Raises:
            ValueError: When trying to find an IPv4 address in a v6 trie and vice-versa.
        """
        for node in self.traverse_preorder_from_node(self.root):
            yield node

    def traverse_preorder_from_node(self, node: PatriciaNode) -> PatriciaNode:
        """Perform a preorder traversal of the trie from a given node.

        Args:
            node: The node to traverse from.

        Yields:
            PatriciaNode: The next node in the traversal.

        Raises:
            ValueError: When trying to find an IPv4 address in a v6 trie and vice-versa.
        """
        stack = []
        cur_node = node
        while len(stack) > 0 or cur_node is not None:
            while cur_node is not None:
                stack.append(cur_node)
                yield cur_node
                cur_node = cur_node.left

            if len(stack) > 0:
                cur_node = stack.pop()
                cur_node = cur_node.right

    def traverse_postorder(self) -> PatriciaNode:
        """Perform a postorder traversal of the trie from a given node.

        Yields:
            PatriciaNode: The next node in the traversal.

        Raises:
            ValueError: When trying to find an IPv4 address in a v6 trie and vice-versa.
        """
        for node in self.traverse_postorder_from_node(self.root):
            yield node

    def traverse_postorder_from_node(self, node: PatriciaNode) -> PatriciaNode:
        """Perform a postorder traversal of the trie from a given node.

        Args:
            node: The node to traverse from.

        Yields:
            PatriciaNode: The next node in the traversal.

        Raises:
            ValueError: When trying to find an IPv4 address in a v6 trie and vice-versa.
        """
        stack = []
        cur_node = node
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
