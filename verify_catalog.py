import mh_tracker
import sqlite3

mh_tracker.init_db()
conn = sqlite3.connect('monster_high_inventory.db')
cur = conn.cursor()
cur.execute('SELECT COUNT(DISTINCT character) FROM catalog_dolls')
print('distinct_characters', cur.fetchone()[0])
cur.execute("SELECT character, COUNT(1) FROM catalog_dolls WHERE character IN ('Abbey Bominable','Ghoulia Yelps','Cleo de Nile','Draculaura','Frankie Stein') GROUP BY character ORDER BY character")
print(cur.fetchall())
