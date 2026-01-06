from tickets_parser import parse_ticket_message, extract_category_price_pairs, normalize_text
import re

raw_text = """
parsing a mesage ticket 
this is a real exmaple  
Available 
Wc 2026

3 x4 cat 3 - 1200$
13 x4 cat 4 - 400$
17 x4 cat 4 - 475$
17 x2 cat 3 - 499$
19 x4 cat 3 - 975$
29 x3 cat 2 - 899$
31 x4 cat 3 - 275$
34 x4 cat 3 - 275$
49 x1 cat 2 - 1100$
49 x2 cat 2 - 1250$
49 x4 cat 2 - 1400$
56 x3 cat 3 - 799$
79 x4 cat 4 - 999$
80 x4 cat 3 - 699$
84 x4 cat 2 - 899$
86 x4 cat 1 1400$
86x4 cat 2 - 1300$
92 x4 cat 4 - 1099$
95 x4 cat 3 - 899$
95 x4 cat 2 - 1199$
98 x2 cat 3 - 1400$
100 x4 cat 3 - 1400$
101 x2 cat 2 - 2875$

for exmaple  for WC2026 
match  3 
x4  tickets  
 cat 3  for price  - 1200$
"""

print(f"Original Text Length: {len(raw_text)}")
normalized = normalize_text(raw_text)
print(f"Normalized: {normalized[-100:]}") # Show end of normalized text

print("\n--- Testing Current Extract ---")
lines = extract_category_price_pairs(normalized)
print(f"Found {len(lines)} lines")
for line in lines:
    print(line)

print("\n--- Testing Parse Full ---")
result = parse_ticket_message(raw_text)
print(f"Top Match: {result['match']}")
print(f"Lines Match Counts:")
from collections import Counter
matches = [l.get('match') for l in result['lines']]
print(Counter(matches))
