import sqlite3
c = sqlite3.connect('prices.db')
r = c.execute('SELECT category, price FROM price_history WHERE match_name LIKE \"%Match 1%\" ORDER BY category LIMIT 4').fetchall()
print('\n📊 MATCH 1 (Mexico vs South Africa) PRICES:\n')
for x in r:
    print(f'   {x[0]}: \')
c.close()
