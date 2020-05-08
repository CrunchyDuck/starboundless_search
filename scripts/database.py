"""This object will handle SQLite3, JSON, and checksum operations."""
try:
	from pathlib import Path # Allows me to fetch a list of all files within an area easily.
	from subprocess import run # Used to unpack the .pak files.
	from os import (
		mkdir as makedir, # I renamed this because I was using "makedirs" and switched to this.
		path
	)
	from shutil import rmtree
	from hashlib import md5 # Used to generate checksums and verify files.
	import re
	import logging
	import sqlite3
	import json
	from datetime import datetime
except ModuleNotFoundError as e:
	print("{}\nThis likely means that there's a file missing. If so, please contact me (CrunchyDuck) and show me this error message.".format(e))
	input()
	exit()


def Database(steamapps_directory):
	object = database()
	object.steam_dir = Path(steamapps_directory)
	object.mods_dir = Path(str(object.steam_dir) + "/workshop/content/211820")  # Folder for steam mods.
	object.starbound_dir = Path(str(object.steam_dir) + "/common/Starbound")  # Starbound folder
	object.starbound_mods_dir = Path(str(object.starbound_dir) + "/mods")  # Location of the mods folder in the starbound folder
	return object



class database():

	def __init__(self):
		self.program_folder = str(Path.cwd().parent) # The location of this program's master folder.
		self.data_folder = "{}/data".format(self.program_folder)

		# Set when the object is called. These are all Path objects.
		self.steam_dir = "" # This will be used to search for starbound's files.
		self.mods_dir = ""  # Folder for steam mods.
		self.starbound_dir = ""  # Starbound folder
		self.starbound_mods_dir = ""  # Location of the mods folder in the starbound folder

		# Database
		db_file = self.data_folder + "/recipe_test.foxdb" # Location of the database file on the PC.
		b_make_db = False # If we detect the file missing, or detect any missing tables, create them.
		if not path.isfile(db_file):
			b_make_db = True

		self.connect = sqlite3.connect(db_file)  # Open the SQL database on the PC.
		self.connect.isolation_level = None
		self.cursor = self.connect.cursor()  # I don't quite understand how the cursor works, but it's the main thing used when interacting with the database.
		self.connect.create_function("REGEXP", 2, self.regexp)

		# If the file was detected, check if all tables are present.
		# TODO - Add this. I couldn't find a way to get the number of tables easily, so I'll do it later.
		# self.db_tables = ["recipes", "objects", "learn", "id_convert"]
		if b_make_db:
			self.create_tables(self.cursor)

		self.re_block_comment = re.compile(r'(/\*)(.|\n)*(\*/)') # This is used to search a JSON file for block comments.

		# Declares many more variables that may need to be reset at times.
		self.reset()



	def index_mods(self):
		# Search for all mods in the user's files (steam mods and on disk mods)
		self.reset() # This will make sure that all variables that could have been used will be reset.

		starbound_mod_files = list(self.starbound_mods_dir.glob("*.pak"))  # All mods within the starbound mod directory.
		steam_mod_files = list(self.mods_dir.glob("**/*.pak"))  # Get all .pak stored within the steam mod directory
		all_mods = starbound_mod_files + steam_mod_files # Since we're checking mods based on their checksums, where they come from won't change how we handle them.
		all_mods.append(str(self.starbound_dir) + "/assets/packed.pak") # This will add the baseg game assets in. You know, just in case.

		with open(self.program_folder + "/data/modlist.fox") as f:
			self.indexed_checksums = re.findall(r"(^.*)(?=/)", f.read(), flags=re.M) # A list of all mods that we have already indexed.
			f.seek(0)
			self.indexed_names = re.findall(r"(?<=/).*", f.read(), flags=re.M) # All of the names to complement the checksums so we can identify them.
			# TODO here. I'm going to change this over to an SQL database, so if the DB gets corrupted it'll automatically deal with the modlist.

		for mod in all_mods:
			mod_id = self.generate_checksum(mod)
			if mod_id not in self.indexed_checksums:
				logging.debug("New checksum {} found".format(mod_id))
				self.mod_files.append(str(mod))
				self.mod_checksums.append(mod_id)
			else:
				logging.debug("Existing checksum {} found...".format(mod_id))
				self.found_mods.add(mod_id)

		# Check if there are any mods that were NOT found from the modlist we had kept.
		previous_modlist = []
		for i in range(int(len(self.indexed_checksums))):
			previous_modlist.append(self.indexed_checksums[i]) # Fetch all checksums from the modlist.
		previous_modlist = set(previous_modlist) # Turn it into a set so that we can easily remove duplicates.

		# Report undetected checksums.
		self.undetected_checksums = previous_modlist - self.found_mods
		if self.undetected_checksums: # This will be True if there's items in this set.
			self.b_lost_mods = True
			for id in self.undetected_checksums:
				lost_index = self.indexed_checksums.index(id) # What position the lost checksum is in.
				lost_name = self.indexed_names[lost_index]
				self.lost_mods.append(lost_name)

				logging.info("Mod {} was not found. Mod may have been removed or updated".format(lost_name))

		return "OK" # I don't know what else to return so I'll just leave something I can use to check it was successful.

	def update(self):
		# TODO - Maybe I can allow the user to unpack in one session, and then parse them on another?
		# Once we've verified which checksum are okay/not found/new, unpack the new assets so we can parse them and store their data.

		# Unpack all mods we don't recognize
		if self.b_new_mods:
			unpack_exe = str(self.starbound_dir) + "/win32/asset_unpacker.exe" # The location of teh asset unpacker. This converts .pak files into their source code.
			unpack_location = "{}/unpack".format(self.program_folder) # The unpack directory in this program.

			# Verify the unpack too exists on the user's computer.
			if not Path(unpack_exe).exists:
				logging.critical("""Could not find asset_unpacker.exe in the Starbound files.
				You haven't deleted it, have you? If you have, why on earth-.
				It should be located at {}
				If it is missing, please verify the integrity of your game files.
				If it is not, contact me so I can figure out where my code is stupid.""".format(unpack_exe))
				exit() # Close the program because it cannot possibly run.

			# Clear any existing unpack files. Just in case.
			if Path(unpack_location).exists():
				rmtree(unpack_location) # This will remove any files from the last unpacks that might not have gotten cleaned up.
			makedir(unpack_location)


			# Unpack mods.
			for index, mod in enumerate(self.mod_files):
				logging.debug("Unpacking {}...".format(mod))

				mod_unpack_location = "{}/{}".format(unpack_location, self.mod_checksums[index])  # The place we'll unpack mods temporarily to parse through. Each mod will have its own folder within this. The folder name will be its checksum.
				makedir(mod_unpack_location)
				asset_packed_path = mod
				unpack_command = "{} \"{}\" \"{}\"".format(unpack_exe, asset_packed_path, mod_unpack_location)

				run(unpack_command) # Unpack the files. There's almost certainly going to be errors with this that I cannot fathom, so I'll need to rely on community testing.
				with open(self.program_folder + "/data/modlist.fox", "a") as f: self.indexed_checksums.write(self.mod_checksums[index] + "\n")
				# TODO: Get name of object from metadata here.

				logging.debug("Finished unpacking {}".format(mod))
				break

			# Update the database with the unpacked mods
			def update_database(unpacked_mods_dir):  # With the newly unpacked mods, we need to go over all the files and pick out the important data.
				def get_recipes():
					return directory_of_recipes

				def get_objects():
					# File extensions that contain data we'll need:
					# .liqitem, .object .matitem, .chest, .legs, .head, .activeitem, .augment, .back, .beamaxe, .consumable, .currency, .flashlight, .harvestingtool, .inspectiontool, .instrument, .item, .miningtool,, .objectdisabled, .painttool,
					# .thrownitem, .tillingtool, .wiretool, .projectile
					# .material files are for placed blocks - Useful but not here. .monstertype is for monsters.
					return directory_of_objects

				def update_objects():
					def update_learnDB():  # This database will contain any recipe that is learned from picking up an object, and what you learn from it.
						return nothing

					return nothing

				def update_recipes():
					def update_inputDB():  # The input db needs to be separate from the update db because it is often an array
						return nothing

					def update_outputDB():  # It's possible I'll need to do the same as the input DB, as it is *possible* albeit uncommon for a mod to have multiple outputs.
						return nothing

					return nothing

		# Go over any mods that are missing.
		if self.b_lost_mods:
			# Delete their entries in databases

			# If there are any
			pass

	def unpack(self, filepath):
		"""
		Unpacks files using Starbound's tool provided for it.
		:param filepath: (str) The location of the .pak file to unpack.
		:return: (str) Directory files were unpacked to
		"""
		return unpacked_dir

	def fill_db(self, filepath, checksum):
		"""
		This will fill the database with the contents of an unpacked mod.
		:param filepath: (str) The directory of the unpacked files
		:param checksum: (str) The checksum of the file before it was unpacked, for indexing purposes.
		"""
		dir = Path(filepath)
		self.connect.execute("begin")

		# Create modlist
		# TODO: Apparently the metadata file is optional, so I need to find a way to deal with that in the event that a mod doesn't include it. Likely I'll just use the checksum as a backup.
		meta = str(dir) + "/_metadata"
		read_data = self.read_json(meta) # The contents of the file.
		fields = ["name", "friendlyName", "author", "version"] # This will contain all fields that can be handled in a similar/same way. Other fields may be done manually.
		values = [] # A generic field we'll store things in temporarily

		# Search for all data we can pull.
		for field in fields:
			try:
				values.append(read_data[field])
			except KeyError:
				values.append("?")
				logging.info("Could not find {} while searching {}".format(field, Path(meta).name))
		from_mod = values[0] # This will be used by following fields to indentify which mod this came from.

		self.cursor.execute("INSERT INTO modlist VALUES (?, ?, ?, ?, ?)", (checksum, values[0], values[1], values[2], values[3]))

		# List of all file extensions we need to parse. for now I'm just using this to find where all recipes are learned from.
		extensions = ["liqitem", "object", "matitem", "chest", "legs", "head", "activeitem", "augment", "back", "beamaxe", "consumable", "currency", "flashlight", "harvestingtool", "inspectiontool", "instrument", "item", "miningtool", "objectdisabled", "painttool", "thrownitem", "tillingtool", "wiretool", "projectile"]
		all_files = []

		for e in extensions:
			all_files += list(dir.glob("**/*.{}".format(e)))

		# Create learned list. This will normally be created *at the same time* as the object list.
		learned_list = []
		for file in all_files:
			read_data = self.read_json(str(file))
			itemname = "?"
			learned = ""

			try:
				learnedList = read_data["learnBlueprintsOnPickup"]
				for i in learnedList:
					learned += "{}/".format(i)
				learned = learned[:-1]
			except KeyError:
				continue

			try:
				itemname = read_data["itemName"]
			except KeyError:
				try:
					itemname = read_data["objectName"]
				except KeyError:
					logging.warning("Could not find itemName in {}".format(Path(file).name))

			if learned:
				learned_list.append((itemname, learned, from_mod))

		insert_alone_time = 0
		start_time = datetime.now()
		for i in learned_list:
			in_time = datetime.now()
			self.cursor.execute("INSERT INTO learn VALUES (?, ?, ?)", i)
			out_time = datetime.now()

			difference = out_time - in_time
			if insert_alone_time != 0:
				insert_alone_time = (insert_alone_time + difference) / 2
			else:
				insert_alone_time = difference
		end_time = datetime.now()
		elapsed_time = end_time - start_time

		print("Inserted at an average speed of {} per object across {}".format(insert_alone_time, elapsed_time))

		# Create recipe list
		recipes = list(dir.glob("**/*.recipe"))
		collected_recipes = [] # I'm going to collect all of the recipes and commit them to the database in an executemany to (hopefully) speed the process up.
		recipes_average_time = 0
		for file in recipes:
			in_time = datetime.now()
			read_data = self.read_json(str(file))
			input = ""
			output = ""
			station = ""
			duration = 0
			name = "" # Originally I chose the name to be the name of the file, but I'm instead going to name it after the output.

			# Get inputs.
			try:
				input_field = read_data["input"]

				try:  # Input stores an array of dictionaries
					for i in input_field:
						input += "{}/{}/".format(i["item"], i["count"])
					input = input[:-1]
				except KeyError:  # Input stores a dictionary
					input = "{}/{}".format(input_field["item"], input_field["count"])
			except KeyError:
				logging.warning("Could not read input from file {}".format(Path(file).name))
				input = "?"

			# Get outputs.
			try:
				output_field = read_data["output"]

				try:  # Output stores a dictionary
					name = output_field["item"]
					output = "{}/{}".format(name, output_field["count"])
				except KeyError:  # Output stores an array of dictionaries
					for i in output_field:
						name += i["item "] # I'm not sure how this will look but hopefully this never happens please modders
						output += "{}/{}/".format(name, i["count"])
					output = output[:-1]
					name = name[:-1]
					logging.warning("File {} is using an array for its output instead of a single dictionary. You monster.".format(file))
			except KeyError:
				output = "?"
				logging.warning("Could not read output from file {}".format(Path(file).name))

			# Get station.
			try:
				groups = read_data["groups"]
				station = groups[0] # The first entry should always be the entry of the table.
			except KeyError:
				station = "?"
				logging.warning("Could not read input from file {}".format(Path(file).name))

			# Get duration
			try:
				duration = read_data["duration"]
			except KeyError:
				duration = 0.1 # Thank you to Pixelflame5826#1645 on Discord for helping me out here <3
				logging.debug("Duration not specified in file {}".format(Path(file).name))

			collected_recipes.append((name, station, duration, input, output, from_mod))
			out_time = datetime.now()
			time = out_time - in_time
			if recipes_average_time != 0:
				recipes_average_time = (recipes_average_time + time) / 2
			else:
				recipes_average_time = time

		#print("Average recipes time: {}".format(recipes_average_time))

		in_time = datetime.now()
		self.cursor.executemany("INSERT INTO recipes VALUES(?, ?, ?, ?, ?, ?)", collected_recipes)
		out_time = datetime.now()

		recipe_num = len(collected_recipes)
		diff = out_time - in_time
		print("It took {} to insert all recipes for an average of {} per recipe.".format(diff, diff / recipe_num ))



		if False: # Temporarily taken out so I can test with the recipe database only.
			# Index active items
			# TODO: Many weapons have "builderConfig"s. These are essentially ways that the item can be created, E.G a staff may have fire, ice, electric etc. I need to include this some how if possible. Maybe check the wiki for inspiration.
			# I'll need to learn to read lua to do this, it seems, so that makes me sad.
			files = list(dir.glob("**/*.activeitem"))
			fields = ["itemName", "power", "knockback", "level"]
			# TODO: I really need to change how I treat an object based on its "category", rather than just hoping for the best.
			for file in files:
				read_data = self.read_json(str(file))
				values = []
				generic = self.generic_object_data(file, from_mod, table = "weapon")

				# If the item is one handed, parse it generically.
				if not generic[3]:
					for field in fields:
						try:
							values.append(read_data[field])
						except KeyError:
							values.append("?")
							logging.info("Could not find {} while searching {}".format(field, Path(file).name))
						values.append("None") # There will be no alt ability as it is a single handed item

				# If the object is two handed we'll need to parse it differently
				else:
					# Get name
					try:
						values.append(read_data["itemName"])
					except KeyError:
						values.append("?")
						logging.info("Could not find itemName while searching {}".format(Path(file).name))

					# Attempt to search for primary and secondary ability
					try:
						primary = read_data["primaryAbility"]
						new_fields = ["power", "knockback"] # These are the fields we want to find either in the .projectile, or in projectileParameters
						projectile = primary["projectileType"] # The type of projectile shot will determine default values.
						powerProjectile = None # These is also a "power projectile" type on bows, which is likely the projectile used when perfectly timed.
						projectile_parameters = primary["projectileParameters"]
						projectile_default = None # TODO We need to create a table for .projectiles, and then read the value of the projectile to here to reference if an attempt fails.

						# Attempt to fetch projectile parameters. Should If it fails, should search the projectileType's values instead.
						for new_field in new_fields:
							try:
								values.append(projectile_parameters[new_field])
							except KeyError: # Find the value in the .projectile instead.
								values.append("?")
								pass
					# Likely means it uses a builder instead.
					except KeyError:
						values.append("?")
						values.append("?")

					# Get level
					try:
						values.append(read_data["level"])
					except KeyError:
						values.append("?")
						logging.info("Could not find level while searching {}".format(Path(file).name))

					# Get alt ability
					values.append("?")

				self.cursor.execute("INSERT INTO weapon VALUES (?, ?, ?, ?, ?, ?)", (values[0], values[1], values[2], values[3], values[4], from_mod))

		self.connect("commit")
		self.connect.commit()

	def remove_entries_of_mod(self, mod_name):
		tables = ["modlist", "learn", "id_convert", "recipes", "objects"]

		for table in tables:
			expr = "DELETE FROM {} WHERE from_mod=?".format(table)
			self.cursor.execute(expr, (mod_name,))
			self.connect.commit()

	def search(self, table, column="", where_value="", regex=False, order=""):
		"""
		Search database.
		Supports regex by filling out "where_value" like "REGEXP {}".

		:param table: The table to select data from
		:param column: Which column to select from in the table
		:param where_value: What value to search for (required if column is used). Must include comparator if not regex (such as =, >= etc)
		:param regex: Whether the "order" is a regular expression
		:param order: What field(s) to order the list by
		:return: All matching results
		"""

		expr = "SELECT * FROM {}".format(table)
		if column != "":
			expr += " WHERE {} ".format(column)
			if regex:
				expr += "REGEXP ?"
			else:
				expr += "{}".format(where_value)

		if order != "":
			expr += " ORDER BY {}".format(order)

		if(regex):
			self.cursor.execute(expr, [(where_value)])
		else:
			self.cursor.execute(expr)

		return self.cursor.fetchall()



	# Private functions. Things that will only be used within this class.
	def generic_object_data(self, directory, from_mod, table="None"):
		"""
		:param dictionary: The directory to parse for generic data.
		:param table: The location of the companion detailed table that this object will contain. "None" is default.
		:param from_mod: The name of the mod this entry belongs to.
		:return: Returns array of parsed data
		"""
		# TODO: Make this to simply get the data, and not automatically submit it.
		read_data = self.read_json(str(directory))
		fields = ["itemName", "shortdescription", "price", "twoHanded", "category", "rarity", "description"]
		values = []

		for field in fields:
			try:
				values.append(read_data[field])
			except KeyError:
				if field == "twoHanded":
					values.append(0)
					continue
				elif field == "itemName":
					try:
						values.append(read_data["objectName"])
						continue
					except KeyError:
						values.append("?")
				else:
					values.append("?")
				logging.warning("Could not find {} for generic table while searching {}".format(field, Path(directory).name)) # TODO add in more detail about which file is being checked.


		self.cursor.execute("INSERT INTO objects VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (values[0], values[1], values[2], values[3], values[4], values[5], values[6], table, from_mod))
		return values

	def get_path_name(self, directory):
		dir_len = len(directory)
		filename = ""

		for i in range(dir_len):
			if directory[-i] == "\\":
				for j in range(i):
					filename = filename + directory[-i + j]
				break
		return filename

	def read_json(self, file_path):
		"""Attempts to read the contents of a JSON file. As Starbound allows for comments in its files, I need to be able to delete these comments if they arise.
		:return: Returns a dictionary of the JSON file, or None if the operation failed.
		"""
		with open(file_path) as file:
			try:
				data = json.load(file)
				return data
			except json.decoder.JSONDecodeError as e:
				logging.warning("Erroneous JSON code in {}, attempting to fix...".format(Path(file_path).name))

				file.seek(0)  # We've already read the file once, so reset the seek.
				new_file = file.read()  # Convert the file to a string so we can run functions on it.

				# Search for inline comments.
				while True:  # Will automatically break out if it find no comments.
					comment_start = new_file.find("//") # TODO - I've seen // be used in actual values (e.g "name": "//duck". I should change this to regex so I can account for this in the future.
					if comment_start == -1:
						break
					else:
						linebreak = new_file.find("\n", comment_start)
						comment = new_file[comment_start:linebreak]
						new_file = new_file.replace(comment, "")  # Okay I really should be using RegEx here, but it's been years since I touched it an I can't be bothered to learn it again right now.

				# Search for block comments.
				while True:
					match = re.search(self.re_block_comment, new_file)
					if match:
						comment_start = match.start(0)
						comment_end = match.end(0)
						comment = new_file[comment_start:comment_end]
						new_file = new_file.replace(comment, "")
					else:
						break
				#print(new_file)

				# Try to read the string again after all comments have been removed.
				try:
					data = json.loads(new_file)  # Changed to loads with an s as we're reading a string, not a file.
					logging.info("Successfully removed comments!")
					return data
				except Exception as e:
					logging.warning("Cannot load file, error {}. Skipping file...".format(e))
					data = None
					return data

	def reset(self):
		"""Defines and or resets all of the self. variables I will be using."""
		self.mod_files = []  # The directories of all mods the user has with an unrecognized checksum.
		self.mod_checksums = []  # All of the file checksums of the mods, essentially their identification. We'll add these to modlist.fox when we're done.
		self.mod_names = []  # Will contain all of the names in the metadata.
		self.undetected_checksums = set({})  # Any checksums that were not found. These will be mods we'll need to search for in case they have been updated.
		self.found_mods = set({})  # These are all of the mod checksums from the files that we DO recognize.
		self.indexed_checksums = []  # All checksums in modlist.fox
		self.indexed_names = []  # All mod names in modlist.fox. The index in this list should relate to the checksum of self.indexed_checksums
		self.lost_mods = []  # A list of the names of all mods that could not be found. We'll use this name to remove any entries that were added by this mod.

		self.b_new_mods = False  # This will evaluate if there's a new mod detected. New mods should be pulled from self.mod_files
		self.b_lost_mods = False  # Whether there are mods that used to be on here, but are no longer detected.

	def create_tables(self, cursor):
		### CREATE TABLES ###
		cursor.execute("begin")

		# Objects table
		cursor.execute("""CREATE TABLE objects (
			item_name TEXT,
			display_name TEXT,
			price INTEGER,
			two_handed INTEGER,
			category TEXT,
			rarity TEXT,
			description TEXT,
			detailed_table TEXT,
			from_mod TEXT
			)""")

		# Recipes table
		cursor.execute("""CREATE TABLE recipes (
			name TEXT,
			station TEXT,
			duration REAL,
			input TEXT,
			output TEXT,
			from_mod TEXT
			)""")

		# Learning table
		cursor.execute("""CREATE TABLE learn (
			from_object TEXT,
			recipes TEXT,
			from_mod TEXT
			)""")

		# ID to Name table.
		cursor.execute("""CREATE TABLE id_convert (
			id TEXT,
			name TEXT,
			from_mod TEXT
			)""")

		# Modlist table.
		cursor.execute("""CREATE TABLE modlist (
			checksum TEXT,
			from_mod TEXT,
			friendly_name TEXT,
			author TEXT,
			version TEXT
			)""")

		cursor.execute("commit")

	def regexp(self, expr, item):
		reg = re.compile(expr)
		return reg.search(item) is not None


	def generate_checksum(self, file_path):
		#logging.debug("Generating checksum for file located at {}...".format(file_path))
		hash_md5 = md5()
		with open(file_path, "rb") as f:
			for chunk in iter(lambda: f.read(4096), b""):
				hash_md5.update(chunk)
		checksum = hash_md5.hexdigest()

		return checksum


if __name__ == "__main__":
	program_folder = str(Path.cwd().parent)  # The location of this program's master folder.
	logging.basicConfig(filename='{}/log.txt'.format(program_folder), filemode="w", level=logging.DEBUG, format="[%(asctime)s] %(levelname)s: %(message)s", datefmt="%m/%d/%Y %I:%M:%S %p")
	d = Database("E:/Steam/steamapps")
	d.index_mods()
