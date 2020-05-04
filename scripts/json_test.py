import json
import sqlite3
from pathlib import Path
import os
import datetime
import re


def err(file, string, should_print):
	"""Add the error message into the file, and optionally print the error to the console."""
	# This is going to be replaced with a better system in final release.
	pass


def create_table(cursor):
	"""Create an SQL table"""
	# The output of a recipe might be able to make multiple of
	cursor.execute("""CREATE TABLE recipes (
		name string,
		station string,
		duration real,
		input string,
		output string
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

this_folder = Path.cwd().parent
data_folder = Path(str(this_folder) + "/data")
scripts_folder = Path(str(this_folder) + "/scripts")
images_folder = Path(str(this_folder) + "/images")

recipes = list(recipe_folder.glob("**/*.recipe"))  # Fetch all .recipe files within this directory and all subdirectories.

log_file = ""


mode = "read"

in_time = datetime.datetime.now() # This will be used to calculate how long the operation took.

if mode == "read":
	conn = sqlite3.connect(str(data_folder) + "/recipe_test.foxdb")  # Open the SQL database on the PC. (Need to look into specifying a path for this to create to.)
	cur = conn.cursor()  # I have no clue, but it seems to relate to the information stored within the database we've opened.
	results = cur.execute("SELECT * FROM recipes")
	for result in cur.fetchall():
		print(result)


if mode == "search":
	with open(str(data_folder) + "/recipe_names.fox") as f:
		txt = f.read()

	x = re.findall(".*rob.*", txt, re.IGNORECASE)
	for i in x:
		print(i)


if mode == "create":
	os.remove(str(data_folder) + "/recipe_test.foxdb") # Remove an existing database.
	conn = sqlite3.connect(str(data_folder) + "/recipe_test.foxdb") # Open the SQL database on the PC. (Need to look into specifying a path for this to create to.)
	cur = conn.cursor() # I have no clue, but it seems to relate to the information stored within the database we've opened.


	create_table(cur)
	recipes = list(recipe_folder.glob("**/*.recipe")) # Fetch all .recipe files within this directory and all subdirectories.
	for recipe in recipes:
		recipe_name = get_name(recipe)

		# Attempt to read the JSON file.
		with open(recipe) as file:
			try:
				data = json.load(file)
			except json.decoder.JSONDecodeError as e:
				err(log_file, "Erroneous JSON code in {}, attempting to fix...".format(recipe_name), True)


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
					err(log_file, "Successful!", True)
				except Exception as e:
					err(log_file, "Cannot load file, error {}. Skipping file...".format(e), True)
					continue

		# Index materials for crafting
		try:
			craft_materials = data["input"]

			try:
				inputs = ""
				for item in craft_materials:
					inputs += "{}/{}/".format(item["item"], item["count"])
				inputs = inputs[:-1] # Remove the last character, as it will always be a forward slash.

			except TypeError: # In the event that some how it's formatted as a single value.
				inputs = "{}/{}".format(craft_materials["item"], craft_materials["count"])

		except KeyError:
			err(log_file, "No input defined in {}".format(recipe_name), False)
			inputs = "UNKNOWN"

		# Index what's created
		try:
			outputarr = data["output"]

			try:
				outputs = "{}/{}".format(outputarr["item"], outputarr["count"])

			except TypeError: # For handling multiple outputs
				outputs = ""

				for item in outputarr:
					outputs = "{}/{}/".format(item["item"], item["count"])
				outputs = outputs[:-1]

		except KeyError:
			err(log_file, "No output defined in {}".format(recipe_name), False)
			outputs = "UNDEFINED"

		# Index what group it's stored in
		try:
			groupsarr = data["groups"]
			station_name = groupsarr[0]

		except KeyError:
			err(log_file, "No station name in {}".format(recipe_name), False)
			station_name = "UNDEFINED"

		# Index crafting duration
		try:
			duration = data["duration"]

		except KeyError:
			err(log_file, "No duration key in {}".format(recipe_name), False)
			duration = -1 # Duration isn't listed so we'll have to mark it as unknown.

		# Create entry in SQL table
		cur.execute("INSERT INTO recipes VALUES (?, ?, ?, ?, ?)", (recipe_name, station_name, duration, inputs, outputs))
		conn.commit()

out_time = datetime.datetime.now()
difference = out_time - in_time
print(difference)
