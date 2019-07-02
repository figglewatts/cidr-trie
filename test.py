from cidr_trie import PatriciaTrie

test = """1.0.0.0/24=13335
2.104.109.0/24=2386
12.104.63.0/24=14119
"""

if __name__ == "__main__":
    trie = PatriciaTrie()

    i = 0
    for line in test.split('\n'):
        if len(line) == 0:
            continue
        p = line.split('=')
        prefix = p[0]
        trie.insert(prefix, i)
        i += 1

    print(trie.find_all_values("1.0.0.0"))