import sqlite3
import os


conn = sqlite3.connect("test.foxdb") # Open the SQL database on the PC. (Need to look into specifying a path for this to create to.)
cursor = conn.cursor() # I have no clue, but it seems to relate to the information stored within the database we've opened.

# Create an SQL table
cursor.execute("""CREATE TABLE item (
	image_id text,
	name text,
	category text,
	price integer,
	rarity text,
	description text,
	learn_from text,
	itemid integer,
	can_craft integer,
	station string,
	input string,
	output string
	)""")


# Insert an element into an existing SQL table.
cursor.execute("INSERT INTO employees VALUES ('Adolf', 'Hitler', 61)")
conn.commit()

cursor.execute("SELECT * FROM employees WHERE last='Hitler'")
print(cursor.fetchone())
conn.commit()


# Clean up
conn.close()
current_dir = os.getcwd()
os.remove(current_dir + "/" + "test.foxdb")
