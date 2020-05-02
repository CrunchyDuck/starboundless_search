import json
import sqlite3
from pathlib import Path
import os
import datetime


def err (file, string, should_print):
	"""Add the error message into the file, and optionally print the error to the console."""
	file += "\n" + string
	if should_print:
		print(string)


def create_table(cursor):
	"""Create an SQL table"""
	cursor.execute("""CREATE TABLE recipes (
		name string,
		station string,
		duration real,
		input string,
		output string
		)""")

	cursor.execute("""CREATE TABLE inputs (
		recipe string,
		item string,
		count integer
		)""")


def search(cursor):
	# Our search function
	cursor.execute("SELECT * FROM recipes WHERE last='Hitler'")
	return cursor.fetchone()


def cleanup(connection):
	# Clean up
	# os.remove(os.getcwd() + "/" + "test.foxdb") # Delete file
	connection.close()


def get_name(file_path):
	"""Returns the name of the file at this path without."""
	p = Path(file_path)
	return p.stem


steamapps_path = Path("E:/Steam/steamapps")
master_path = Path(str(steamapps_path))
starbound_path = Path(str(master_path) + "/common/Starbound")
unpacked_folder = Path(str(starbound_path) + "/test_unpack")

recipe_folder = Path(str(unpacked_folder) + "/recipes")

recipes = list(recipe_folder.glob("**/*.recipe"))  # Fetch all .recipe files within this directory and all subdirectories.
error_file = ""

mode = "read"

in_time = datetime.datetime.now() # This will be used to calculate how long the operation took.

if mode == "read":
	conn = sqlite3.connect("recipe_test.foxdb")  # Open the SQL database on the PC. (Need to look into specifying a path for this to create to.)
	cur = conn.cursor()  # I have no clue, but it seems to relate to the information stored within the database we've opened.

	for row in cur.execute("SELECT * FROM recipes ORDER BY name"):
		pass #print(row)

if mode == "create":
	os.remove(os.getcwd() + "/recipe_test.foxdb") # Remove an existing database.
	conn = sqlite3.connect("recipe_test.foxdb") # Open the SQL database on the PC. (Need to look into specifying a path for this to create to.)
	cur = conn.cursor() # I have no clue, but it seems to relate to the information stored within the database we've opened.


	create_table(cur)
	recipes = list(recipe_folder.glob("**/*.recipe")) # Fetch all .recipe files within this directory and all subdirectories.
	for recipe in recipes:
		recipe_name = get_name(recipe)

		with open(recipe) as file:
			try:
				data = json.load(file)
			except json.decoder.JSONDecodeError as e:
				err(error_file, "Erroneous JSON code in {}, attempting to fix...".format(recipe_name), True)


				file.seek(0) # We've already read the file once, so reset the seek.
				new_file = file.read() # Convert the file to a string so we can run functions on it.
				while True: # Will automatically break out if it find no comments.
					comment_start = new_file.find("//")
					if comment_start == -1:
						break
					else:
						linebreak = new_file.find("\n", comment_start)
						comment = new_file[comment_start:linebreak]
						new_file = new_file.replace(comment, "") # Okay I really should be using RegEx here, but it's been years since I touched it an I can't be bothered to learn it again right now.

				# Try to read the string again after all comments have been removed.
				try:
					data = json.loads(new_file) # Changed to loads with an s as we're reading a string, not a file.
					err(error_file, "Successful!", True)
				except Exception as e:
					err(error_file, "Cannot load file, error {}. Skipping file...".format(e), True)
					continue

		# Index materials for crafting
		try:
			craft_materials = data["input"]
			for item in craft_materials:
				cur.execute("INSERT INTO inputs VALUES (?, ?, ?)", (recipe_name, item["item"], item["count"]))
				conn.commit()
		except KeyError:
			err(error_file, "No input defined in {}".format(recipe_name), False)
			cur.execute("INSERT INTO inputs VALUES (?, 'UNKNOWN', 'UNKNOWN')", (recipe_name))
			conn.commit()

		# Index what's created
		try:
			outputarr = data["output"]
			output = "{} ({})".format(outputarr["item"], outputarr["count"])
		except KeyError:
			err(error_file, "No output defined in {}".format(recipe_name), False)
			output = "UNDEFINED"

		# Index what group it's stored in
		try:
			groupsarr = data["groups"]
			station_name = groupsarr[0]
		except KeyError:
			err(error_file, "No station name in {}".format(recipe_name), False)
			station_name = "UNDEFINED"

		# Index crafting duration
		try:
			duration = data["duration"]
		except KeyError:
			err(error_file, "No duration key in {}".format(recipe_name), False)
			duration = -1 # Duration isn't listed so we'll have to mark it as unknown.

		# Create entry in SQL table
		cur.execute("INSERT INTO recipes VALUES (?, ?, ?, ?, ?)", (recipe_name, station_name, duration, recipe_name, output))
		conn.commit()

out_time = datetime.datetime.now()
difference = out_time - in_time
print(difference)
