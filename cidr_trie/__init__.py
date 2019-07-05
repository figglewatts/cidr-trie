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

    # find all node values on the way down
    print(trie.find_all("32.32.32.32"))
"""

import threading

from .cidr_util import is_v6, cidr_atoi, longest_common_prefix_length, get_subnet_mask, ip_itoa
from .bits_util import is_set, ffs
from typing import Any, List, Dict, Tuple


class PatriciaNode:
    """A node in the Patricia trie.

    Attributes:
        ip (int): The IP address associated with this node.
        bit (int): How many bits along the IP the decision is made to branch.
        masks (Dict[int, Any]): The data stored on this node. Maps netmasks to data.
        left (PatriciaNode): The left subtrie of this node. Self pointer if no left node.
        right (PatriciaNode): The right subtrie of this node. Self pointer if no right node.
        parent (PatriciaNode): The parent node of this node. None if root node.
    """
    def __init__(self, ip: int=0, bit: int=0, masks: Dict[int, Any]={}) -> None:
        self.ip = ip
        self.bit = bit
        self.masks = masks
        self.left = self
        self.right = self
        self.parent = None

    def __str__(self):
        return f"IP: {self.ip}, Decision bit: {self.bit}"

    def get_values(self, prefix: str) -> List[Tuple[str, Any]]:
        """Get values from this node by iterating through netmasks and
        checking to see if the given prefix is contained within.

        Args:
            prefix: The prefix to use to check, i.e. "192.168.0.0/16"
        Returns:
            List[Tuple[str, Any]]: list of tuples of prefixes and values, i.e. [("192.168.0.0/16", 2856), ...]
        """
        # parse the CIDR string
        ip, mask = cidr_atoi(prefix)
        v6 = is_v6(prefix)
        result = []

        # for each mask stored on this node, check to see if the IP given by the
        # prefix masked by the mask is equal to the IP stored in the node
        # this indicates that this IP is within the network defined by the node
        # and particular netmask
        for m in self.masks.keys():
            # if the mask is greater than the given mask, there's no way the
            # prefix can be in this range, as it's bigger than this network
            if m > mask:
                continue

            if self.ip == (ip & get_subnet_mask(m, v6)):
                ip_str = f"{ip_itoa(self.ip, v6)}/{m}"
                result.append((ip_str, self.masks[m]))
        return result

    def get_child_values(self, prefix: str) -> List[Tuple[str, Any]]:
        """Get all child values from this node by iterating through netmasks and
        checking to see if the given prefix is larger than the given netmask.

        Args:
            prefix: The prefix to use to check, i.e. "192.168.0.0/16"
        Returns:
            List[Tuple[str, Any]]: list of tuples of prefixes and values, i.e. [("192.168.0.0/16", 2856), ...]
        """
        # parse the CIDR string
        _, mask = cidr_atoi(prefix)
        v6 = is_v6(prefix)
        result = []

        # for each mask stored in this node, check to see if the netmask is
        # greater than the given netmask
        for m in self.masks.keys():
            if m < mask:
                continue

            ip_str = f"{ip_itoa(self.ip, v6)}/{m}"
            result.append((ip_str, self.masks[m]))
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

        # find all node values on the way down
        print(trie.find_all("32.32.32.32"))

    """
    def __init__(self) -> None:
        self.root = PatriciaNode(bit=-1)
        self.v6 = False
        self.size = 0

    def validate_ip_type_for_trie(self, ip: str) -> None:
        """Make sure this IP is valid for this trie.

        Raises:
            ValueError: if trying to insert a v4 address into a v6 trie and vice-versa.
        """
        v6 = is_v6(ip)
        if v6 == True and self.v6 == False:
            raise ValueError("Cannot store IPv6 prefix in IPv4 trie")
        elif v6 == False and self.v6 == True:
            raise ValueError("Cannot store IPv4 prefix in IPv6 trie")

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
        if self.size == 0:
            # set the v6 value if first insert
            self.v6 = is_v6(prefix)
        
        self.validate_ip_type_for_trie(prefix)
        
        ip, mask = cidr_atoi(prefix)
        
        # traverse the trie until we get to a leaf to check
        last_bit = -2 # -2 as it has to be lower than the root (which is -1)
        cur_node = self.root
        while last_bit < cur_node.bit:
            last_bit = cur_node.bit
            if is_set(cur_node.bit, ip, self.v6):
                cur_node = cur_node.right
            else:
                cur_node = cur_node.left

        # check to see if the IP is equal
        if cur_node.ip == ip:
            cur_node.masks[mask] = data
            return cur_node

        # they're different, so find the rightmost bit where they differ
        differ_bit = 0
        while is_set(differ_bit, cur_node.ip, self.v6) == is_set(differ_bit, ip, self.v6):
            differ_bit += 1

        # special case: if we're inserting a node below the root, we want to
        # set the bit to the rightmost set bit, otherwise the bit will be set
        # to zero, causing other non-subprefix nodes to be inserted below
        # this node erroneously
        if differ_bit == 0:
            differ_bit = (127 if self.v6 else 31) - ffs(ip)

        # travel down the trie to that point
        last_node = PatriciaNode(bit=-2) # -2 as it has to be lower than the root (-1)
        cur_node = self.root
        while last_node.bit < cur_node.bit and cur_node.bit <= differ_bit:
            last_node = cur_node
            if is_set(cur_node.bit, ip, self.v6):
                cur_node = cur_node.right
            else:
                cur_node = cur_node.left

        # create the new node
        to_insert = PatriciaNode(ip, differ_bit, {mask: data})

        # figure out where to put child
        if is_set(to_insert.bit, cur_node.ip, self.v6):
            to_insert.right = cur_node
        else:
            to_insert.left = cur_node

        # set the child's new parent if it isn't pointing back up
        if cur_node.bit > to_insert.bit:
            cur_node.parent = to_insert

        # figure out which side to insert on
        if is_set(last_node.bit, ip, self.v6):
            last_node.right = to_insert
        else:
            last_node.left = to_insert
        to_insert.parent = last_node

        self.size += 1
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
        self.validate_ip_type_for_trie(prefix)

        # parse the CIDR string
        ip, mask = cidr_atoi(prefix)

        # traverse the trie with the given IP
        last_node = None
        for node in self.traverse(prefix):
            last_node = node
            if node.ip == ip:
                break

        ip_exists = False
        mask_exists = False

        if last_node.ip == ip:
            # if the last node's IP equals this IP, the IP exists
            # we now need to check if the mask is in the set of masks
            ip_exists = True
            mask_exists = mask in last_node.masks

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
        self.validate_ip_type_for_trie(prefix)
        ip, _ = cidr_atoi(prefix)
        
        for node in self.traverse(prefix):
            if node.ip == ip:
                return node

        # if we get to here, the node isn't in the trie
        return None

    def find_all(self, prefix: str, children: bool=False) -> List[Tuple[str, Any]]:
        """Find all values for this prefix, traversing the trie at all levels.

        With get all values from common prefixes of 'prefix', then traverse all
        children of 'prefix' to get their values too.

        Args:
            prefix: The prefix to find in the trie.
            children: Whether to find all child values of the exact node found. (Defaults to False, as this isn't performant in large tries)

        Returns:
            List[Tuple[str, Any]]: list of tuples of prefixes and values, i.e. [("192.168.0.0/16", 2856), ...]

        Raises:
            ValueError: When trying to find an IPv4 address in a v6 trie and vice-versa.
        """
        self.validate_ip_type_for_trie(prefix)
        result = []
        ip, _ = cidr_atoi(prefix)
        
        # for each node on the way down
        last_node = None
        for node in self.traverse(prefix):
            result += node.get_values(prefix)
            last_node = node
            if node.ip == ip:
                break

        if children and last_node.ip == ip:
            # for each child node underneath the last found node
            for node in self.traverse_inorder_from_node(last_node):
                result += node.get_child_values(prefix)

        return result

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
        self.validate_ip_type_for_trie(prefix)

        ip, _ = cidr_atoi(prefix)

        # look for a leaf
        last_node = PatriciaNode(bit=-2) # -2 as it has to be lower than the root (-1)
        cur_node = node
        while last_node.bit < cur_node.bit:
            last_node = cur_node
            yield cur_node
            if is_set(cur_node.bit, ip, self.v6):
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
        last_bit = -2 # -2 as it has to be lower than the root (-1)
        cur_node = node
        while len(stack) > 0 or last_bit < cur_node.bit:
            while last_bit < cur_node.bit:
                stack.append(cur_node)
                last_bit = cur_node.bit
                cur_node = cur_node.left

            if len(stack) > 0:
                cur_node = stack.pop()
                yield cur_node
                last_bit = cur_node.bit
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
        last_bit = -2 # -2 as it has to be lower than the root (-1)
        cur_node = node
        while len(stack) > 0 or last_bit < cur_node.bit:
            while last_bit < cur_node.bit:
                stack.append(cur_node)
                yield cur_node
                last_bit = cur_node.bit
                cur_node = cur_node.left

            if len(stack) > 0:
                cur_node = stack.pop()
                last_bit = cur_node.bit
                cur_node = cur_node.right

