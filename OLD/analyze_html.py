with open('match1_full_page.html', 'r', encoding='utf-8') as f:
    html = f.read()

print('HTML file size:', len(html), 'chars')
print()

# Search for known prices
prices = ['4740', '3900', '2679', '3950']
print('Searching for real Match 1 prices...')
for p in prices:
    if p in html:
        print(f'✅ Found: {p}')
        idx = html.find(p)
        print(f'   Context: ...{html[max(0,idx-150):min(len(html),idx+150)]}...')
        print()
    else:
        print(f'❌ NOT found: {p}')
