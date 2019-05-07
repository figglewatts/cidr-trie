from cidr_trie import PatriciaTrie
from cidr_trie.cidr_util import ip_atoi, longest_common_prefix_length
from cidr_trie.bits_util import ffs, fls

trie = PatriciaTrie()
trie.insert("192.0.0.0/8", 1)
trie.insert("192.0.128.0/24", 2)
trie.insert("128.0.0.0/8", 3)

for value in trie.find_all("128.0.128.2"):
    print(value)