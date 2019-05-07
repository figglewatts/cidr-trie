from cidr_trie import PatriciaTrie
from cidr_trie.cidr_util import ip_atoi, longest_common_prefix_length
from cidr_trie.bits_util import ffs, fls

trie = PatriciaTrie()
trie.insert("192.168.0.0/16", 1234)
trie.insert("192.168.111.112", 1111)
trie.insert("192.168.111.0/24", 11)
for node in trie.traverse("192.168.111.112"):
    print(node.value)

print("--------------")

base_ip = ip_atoi("192.168.0.0")
higher_ip = ip_atoi("192.168.111.0")
lower_ip = ip_atoi("192.0.0.0")
odd_ip = ip_atoi("193.168.0.0")
test_base_ffs_equal = ip_atoi("192.172.0.0")

lcp_higher = longest_common_prefix_length(base_ip, higher_ip, False)
lcp_lower = longest_common_prefix_length(base_ip, lower_ip, False)
lcp_odd = longest_common_prefix_length(base_ip, odd_ip, False)
lcp_test_equal = longest_common_prefix_length(base_ip, test_base_ffs_equal, False)
ffs_base = 32 - ffs(base_ip) - 1

# how do we make an LCP equal to the base FFS?
print(f"ffs: {ffs_base}")
print(f"higher lcp: {lcp_higher}")
print(f"lower lcp: {lcp_lower}")
print(f"odd lcp: {lcp_odd}")
print(f"equal lcp: {lcp_test_equal}")

# for node in trie.traverse_inorder():
#     print(f"{cidr_util.ip_itoa(node.ip, False)} - {node.bit}")