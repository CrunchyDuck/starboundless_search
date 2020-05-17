"""This object will handle SQLite3, JSON, and checksum operations."""
try:
	from pathlib import Path # Allows me to fetch a list of all files within an area easily.
	from subprocess import run # Used to unpack the .pak files.
	from os import (
		mkdir as makedir, # I renamed this because I was using "makedirs" and switched to this.
		makedirs,
		path,
		remove
	)
	from shutil import rmtree
	from hashlib import md5 # Used to generate checksums and verify files.
	import re
	import logging
	import sqlite3
	import json
	from datetime import datetime
	import traceback
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


class timer():
	"""Very basic object that is used to track how much time something took."""
	def t_in(self):
		self.time_in = datetime.now()
	def t_out(self):
		self.time_out = datetime.now()
		return self.time_out - self.time_in

class json_reader():
	"""This object is for handling parsing of different types of files into data for the relevant database."""
	def recipe(self, file):
		filename = Path(file).name
		read_data = self.read_json(str(file))
		# generic = self.generic_object_data(read_data, from_mod, already_parsed=True)
		duration = 0
		name = ""  # Originally I chose the name to be the name of the file, but I'm instead going to name it after the output.

		################
		## Get output ##
		################
		try:
			output_field = read_data["output"]
			try:  # Output stores a dictionary
				# Output_field can be under two different names.
				try:
					name = output_field["item"]
				except KeyError:
					name = output_field["name"]
				# Count can be omitted, and it is assumed to be "1" (Thanks to Sayter for verifying this)
				try:
					count = output_field["count"]
				except KeyError:
					count = 1
				outputs.append((name, name, count, from_mod))
			except KeyError:  # Output stores an array of dictionaries
				logging.error("File {} seems to be storing its output incorrectly.".format(filename))
				raise KeyError("Output in file {} was incorrectly defined.".format(filename))
		except KeyError:
			logging.warning("Could not read output from file {}".format(filename))
			raise KeyError("Could not read output from file {}".format(filename))

		################
		## Get inputs ##
		################
		try:
			input_field = read_data["input"]
			try:  # Input stores an array of dictionaries
				for i in input_field:
					try:
						input_name = i["item"]
					except KeyError:
						input_name = i["name"]
					try:
						count = i["count"]
					except KeyError:
						count = 1
					inputs.append((name, input_name, count, from_mod))
			except KeyError:  # Input stores a dictionary
				try:
					input_name = input_field["item"]
				except KeyError:
					input_name = input_field["name"]
				try:
					count = input_field["count"]
				except KeyError:
					count = 1
				inputs.append((name, input_name, count, from_mod))
		except KeyError:
			logging.warning("Could not read input from file {}".format(filename))
			raise KeyError("Could not read input from file {}".format(filename))

		################
		## Get groups ##
		################
		try:
			for group in read_data["groups"]:
				recipes_groups.append((group, name, from_mod))
		except KeyError:
			# I believe that recipes *can* be defined without a recipe group, they just won't be able to be crafted anywhere. Therefore I will index the recipe.
			recipes_groups.append(("?", name, from_mod))
			logging.error("Could not read recipe groups from file {}".format(filename))

		# Get duration
		try:
			duration = read_data["duration"]
		except KeyError:
			duration = 0.1  # Thank you to Pixelflame5826#1645 on Discord for helping me out here <3
		# logging.debug("Duration not specified in file {}".format(Path(file).name))

		collected_recipes.append((name, duration, from_mod))

class database():

	def __init__(self):
		self.program_folder = str(Path.cwd()) # The location of this program's master folder.
		self.data_folder = "{}/data".format(self.program_folder)
		self.unpack_location = "{}/data/unpack".format(self.program_folder)  # Location where files will be unpacked to (string)
		makedirs(self.unpack_location, exist_ok=True)

		# Set when the object is called.
		self.steam_dir = "" # This will be used to search for starbound's files. (Path)
		self.mods_dir = ""  # Folder for steam mods. (Path)
		self.starbound_dir = ""  # Starbound folder (Path)
		self.starbound_mods_dir = ""  # Location of the mods folder in the starbound folder (Path)



		# Database
		db_file = self.data_folder + "/database.foxdb" # Location of the database file on the PC.
		b_make_db = False # If we detect the file missing, or detect any missing tables, create them.
		if not path.isfile(db_file):
			b_make_db = True

		self.connect = sqlite3.connect(db_file)  # Open the SQL database on the PC.
		self.cursor = self.connect.cursor()  # I don't quite understand how the cursor works, but it's the main thing used when interacting with the database.
		self.connect.create_function("REGEXP", 2, regexp)

		# If the file was detected, check if all tables are present.
		# TODO - Add this. I couldn't find a way to get the number of tables easily, so I'll do it later.
		# self.db_tables = ["recipes", "objects", "learn", "id_convert"]
		if b_make_db:
			self.create_tables()
		self.reader = json_reader() # This is used to read unpacked files.

		self.re_line_comment = re.compile(r'//.*') # This can find all line comments in JSON (//Text after this). TODO: I need to name sure this DOESN'T delete comments within keys/values. We'll have issues if it does.
		self.re_block_comment = re.compile(r'(/\*)(.|\n)+?(\*/)') # This is used to search a JSON file for block comments.
		self.re_colour_tag = re.compile(r'\^.*?;') # This will find colour tags in the names of objects, E.G ^orange;nameofobject^reset;

		# Declares many more variables that may need to be reset at times.
		self.reset()

	def testdef(self):
		def testdef2():
			print("yaay")


	# Process for updating the database:
	# index_mods > prime_files > parse_files
	# At each point in this process, it is stopped to allow user input on whether to continue now or later.
	# I also allow a "do all" option so the user can just set it to work and forget about it.
	def full_index(self):
		self.index_mod()
		self.prime_files()
		self.parse_files()

	def index_mods(self):
		# Search for all mods in the user's files (steam mods and on disk mods)
		self.reset() # This will make sure that all variables that could have been used will be reset.

		# Get all mod files the player has, so we can scan them for checksums.
		starbound_mod_files = list(self.starbound_mods_dir.glob("*.pak"))  # All mods within the starbound mod directory.
		steam_mod_files = list(self.mods_dir.glob("**/*.pak"))  # Get all .pak stored within all folders in the steam mod directory
		all_mods = starbound_mod_files + steam_mod_files
		all_mods.append(str(self.starbound_dir) + "/assets/packed.pak") # This will add the base game assets in. You know, just in case they some how lose the whole database. Or there's an update (There won't be)

		# Get all of the indexed checksums from our database, to see which mods do not need to be added.
		self.cursor.execute("SELECT * FROM modlist")
		modlist = self.cursor.fetchall()
		self.indexed_checksums = []
		self.indexed_friendly_names = []
		for mod in modlist:
			self.indexed_checksums.append(mod[0])
			self.indexed_friendly_names.append(mod[1])

		# Get all files that are already staged (already unpacked)
		self.cursor.execute("SELECT checksum FROM unpacked_files")
		cs = self.cursor.fetchall()
		staged_checksums = []
		staged_found = [] # This will stored all of the staged files that we found. If a staged file isn't found, we'll delete it because the user no longer has it.
		for checksum in cs:
			staged_checksums.append(checksum[0])

		# Check the checksum of all mods the player has installed against our database, to see which ones we recognize.
		for mod in all_mods:
			mod_id = generate_checksum(mod)
			# Mod is already indexed.
			if mod_id in self.indexed_checksums:
				logging.debug("Existing checksum {} found".format(mod_id))
				self.found_mods.add(mod_id)
			# Mod is unpacked already and just needs to be parsed.
			elif mod_id in staged_checksums:
				staged_found.append(mod_id)
				logging.debug("Staged checksum {} found".format(mod_id))
			# Mod is not recognized, and should be unpacked.
			else:
				logging.debug("New checksum {} found".format(mod_id))
				self.mod_files.append(str(mod))
				self.mod_checksums.append(mod_id)

		# Check if there are any mods that were NOT found from the modlist we had kept.
		self.undetected_checksums = set(self.indexed_checksums) - self.found_mods
		if self.undetected_checksums:
			self.b_lost_mods = True # This will be True if there are mods we didn't find.
			for id in self.undetected_checksums:
				lost_index = self.indexed_checksums.index(id) # What position the lost checksum is in.
				lost_name = self.indexed_names[lost_index]
				self.lost_mods.append(lost_name)
				logging.info("Mod {} was not found. Mod may have been removed or updated".format(lost_name)) # Report undetected checksums.

		# Check if there were any staged mods that were NOT found.
		undetected_staged = set(staged_checksums) - set(staged_found)
		if undetected_staged:
			# Delete any staged we couldn't detect as they'll no longer be useful
			for checksum in undetected_staged:
				self.remove_staged(checksum)

		new_files = False
		if self.mod_files:
			new_files = True
		return new_files # Will return True if there are unrecognized mods.

	def prime_files(self):
		"""

		:return:
		"""
		# TODO - Maybe I can allow the user to unpack in one session, and then parse them on another?
		# Once we've verified which checksum are okay/not found/new, unpack the new assets so we can parse them and store their data.

		# Unpack all mods we don't recognize
		if self.b_new_mods:
			# Unpack mods that were found to need that.
			for mod in self.mod_files:
				self.unpack(mod, checksum)
			# Maybe I can update the metadata here, to more accurately index them before parsing.

		# Go over any mods that are missing.
		if self.b_lost_mods:
			for mod in self.lost_mods:
				self.remove_entries_of_mod(mod_checksum=mod)
		return "Primed"

	def unpack(self, unpack_target, checksum):
		"""
		Unpacks files using Starbound's tool provided for it.
		:param unpack_target: (str) The location of the .pak file to unpack.
		:param checksum: (str) What to name the folder it's unpacked to.
		:return: (str) Directory files were unpacked to
		"""
		try:
			folder_name = checksum
			unpack_exe = str(self.starbound_dir) + "/win32/asset_unpacker.exe"  # The location of the asset unpacker. This converts .pak files into their source code.
			unpack_location = "{}/unpack".format(self.program_folder)  # The unpack directory in this program.
	
			# Verify the unpack tool exists on the user's computer.
			if not Path(unpack_exe).exists:
				logging.critical("""Could not find asset_unpacker.exe in the Starbound files.
							You haven't deleted it, have you? If you have, why on earth-
							It should be located at {}
							If it is missing, please verify the integrity of your game files.
							If it is not, contact me so I can figure out where my code is stupid.""".format(unpack_exe))
				return "Cannot Unpack"

			# Clear any existing unpack files. Just in case.
			if Path(unpack_location).exists():
				rmtree(unpack_location)  # This will remove any files from the last unpacks that might not have gotten cleaned up.
			makedir(unpack_location)
	
			# Begin unpack
			logging.debug("Unpacking {}...".format(unpack_target))
			mod_unpack_location = "{}/{}".format(unpack_location, folder_name)  # The place we'll unpack mods to parse through. Each mod will have its own folder within this. The folder name will be its checksum.
			makedir(mod_unpack_location)
			asset_packed_path = unpack_target
			unpack_command = "{} \"{}\" \"{}\"".format(unpack_exe, asset_packed_path, mod_unpack_location)

			run(unpack_command)  # Unpack the files. There's almost certainly going to be errors with this that I cannot fathom, so I'll need to rely on community testing.
			self.cursor.execute("INSERT INTO unpacked_files VALUES ?", (checksum,)) # Add this to the list of staged files.
	
			logging.debug("Finished unpacking {}".format(unpack_target))
			return unpacked_dir

		except Exception as e:
			logging.error("Unknown error occurred while attempting to unpack {}. Trackback:\n{}\n".format(unpack_target, traceback.format_exc()))
			return "UNPACK FAILED"

	def parse_files(self):
		"""
		Parse all files that are currently staged.
		"""
		# Get a list of all currently unpacked files
		self.cursor.execute("SELECT checksum FROM unpacked_files")
		staged_files = self.cursor.fetchall()
		for checksum in staged_files:
			folder_dir = self.program_folder + "/{}".format(checksum)
			self.fill_db(folder_dir, checksum)

	def fill_db(self, filepath, checksum):
		"""
		This will fill the database with the contents of an unpacked mod.
		:param filepath: (str) The directory of the unpacked files
		:param checksum: (str) The checksum of the file before it was unpacked, for indexing purposes.
		"""
		dir = Path(filepath)
		# TODO: Figure out why "peacekeeper1" isn't being indexed.

		####################
		## Create modlist ##
		####################
		# TODO: Apparently the metadata file is optional, so I need to find a way to deal with that in the event that a mod doesn't include it. Likely I'll just use the checksum as a backup.
		meta = str(dir) + "/_metadata"
		fields = ["name", "friendlyName", "author", "version"] # This will contain all fields that can be handled in a similar/same way. Other fields may be done manually.
		values = [] # A generic field we'll store things in temporarily
		from_mod = "" # This is the mod that this unpack belongs to.

		##############
		## METADATA ##
		##############
		read_data = self.read_json(meta)
		for field in fields:
			try:
				values.append(read_data[field])
			except KeyError:
				values.append("?")
				logging.info("Could not find {} while searching {}".format(field, Path(meta).name))
		from_mod = values[0] # This will be used by following fields to identify which mod this came from.

		self.cursor.execute("INSERT INTO modlist VALUES (?, ?, ?, ?, ?)", (checksum, values[0], values[1], values[2], values[3]))

		# List of all file extensions we need to parse for useful data.
		extensions = ["liqitem", "object", "matitem", "chest", "legs", "head", "activeitem", "augment", "back", "beamaxe", "consumable", "currency", "flashlight", "harvestingtool", "inspectiontool", "instrument", "item", "miningtool", "objectdisabled", "painttool", "thrownitem", "tillingtool", "wiretool"]
		all_files = []

		for exten in extensions:
			all_files += list(dir.glob("**/*.{}".format(exten)))
		num_of_files = len(all_files)

		start_parsing_files = datetime.now()
		# Search through all decompiled files.
		learned_list = [] # _list variables will store anything that needs to be loaded into a a table. We'll do them in bulk to make it much, much faster.
		stations_groups = []
		object_list = []
		for file in all_files:
			try:
				# Note: Starbound reads the extension of an object (such as .activeitem) to determine what it should search for. I should do the same to emulate what will be available in game.
				self.filename = Path(file).name
				read_data = self.read_json(str(file))
				if read_data == "?":
					logging.error("Could not read JSON file located at {}, skipping file.".format(str(file)))
					continue

				###################
				## Create Object ##
				###################
				item_name = self.json_get("itemName", read_data, error_on_fail=False)
				if item_name == "?": # This might happen if it is a .object file.
					item_name = self.json_get("objectName", read_data, error_message="File {} has no itemName or objectName key. Cannot be indexed.".format(self.filename))
				display_name = self.json_get("shortdescription", read_data, error_message="File {} has no shortdescription key.".format(self.filename))
				category = self.json_get("category", read_data, error_message="File {} has no category key.".format(self.filename))
				if item_name != "?" and category != "?" and display_name != "?":
					object_list.append((item_name, display_name, category, 0, 0, "?", "?", from_mod))


				##################
				## Create Learn ##
				##################
				try:
					learnedList = read_data["learnBlueprintsOnPickup"]
					for learned in learnedList:
						if learned: # I've seen some objects have no values within this field, so I need to check for that.
							learned_list.append((item_name, learned, from_mod))
				except KeyError: # This will trigger if there's nothing to be learned from this object.
					pass


				#####################
				## Crafting Groups ##
				#####################
				# NOTE: If a table doesn't have the "crafting" category tag, I will not be able to find it. This is to optimize the time it takes to scan objects, maybe I'll turn this off in the future if it's not too much of an increase.
				cat = self.json_get("category", read_data, error_on_fail=False)

				if cat == "crafting":
					group = self.json_get("recipeGroup", read_data, error_on_fail=False) # This seems to be an old method they changed from at a later date, but of course they didn't remove it all.
					if group != "?":
						stations_groups.append((group, item_name, from_mod))

					else:
						upgrade_stages = self.json_get("upgradeStages", read_data, error_on_fail=False) # Check if this object has upgrade stages. If so, this will take priority. Hopefully that's how the game does it.
						if upgrade_stages != "?":
							object_list.pop() # I believe that first object in upgrade_stages will always be a duplicate of whatever you find in the rest of the file, so I remove it here.
							for obj in upgrade_stages:

								############################
								## Create new object_list ##
								############################
								params = self.json_get("itemSpawnParameters", obj, error_on_fail=True) # TODO maybe replace this with an actual try/except so I can give more information.
								if params != "?":
									o_item_name = self.json_get("animationState", obj)
									o_display_name = self.json_get("shortdescription", params)
									# Validate the checked values. If they're ?, then inherit the original value.
									if o_item_name == "?": o_item_name = item_name
									if o_display_name == "?": o_display_name = display_name
									if o_item_name != "?" and o_display_name != "?" and category != "?":
										object_list.append((o_item_name, o_display_name, category, 0, 0, "?", "?", from_mod))

									####################
									## stations_group ##
									####################
									values = self.create_group_list(o_item_name, from_mod, obj, dir)
									for entry in values:
										if entry[0] != "?":
											stations_groups.append(entry)

								# Search for addonConfig
								addonConfig = self.json_get("addonConfig", obj, error_on_fail=False)
								if addonConfig != "?":
									usesAddons = self.json_get("usesAddons", addonConfig, error_on_fail=True)

									for addon in usesAddons:
										a_item_name = self.json_get("name", addon)
										addon_data = self.json_get("addonData", addon)
										interact_data = self.json_get("interactData", addon_data)

										###################
										## Create Object ##
										###################
										panel = self.json_get("paneLayoutOverride", interact_data)
										window = self.json_get("windowtitle", panel)
										a_display_name = window["title"]
										if a_item_name != "?" and a_display_name != "?" and category != "?":
											object_list.append((a_item_name, a_display_name, category, 0, 0, "?", "?", from_mod))

										####################
										## stations_group ##
										####################
										filter = self.json_get("filter", interact_data)
										for group in filter:
											if group != "?":
												stations_groups.append((group, a_item_name, from_mod))

						else: # If it has no upgrade stages, check it as a normal object for groups
							interact_data = self.json_get("interactData", read_data)
							if interact_data != "?":
								# Check for filter.
								filter = self.json_get("filter", interact_data)
								if filter != "?":
									for group in filter:
										stations_groups.append((group, item_name, from_mod))
								elif filter == "?":
									# Check config file
									config_location = str(dir) + self.json_get("config", interact_data)
									config = self.read_json(config_location)
									if config != "?":
										filter = self.json_get("filter", config)
										for group in filter:
											stations_groups.append((group, item_name, from_mod))
								elif filter == "config":
									config_location = str(dir) + self.json_get("config", interact_data)
									config = self.read_json(config_location)
									if config != "?":
										filter = self.json_get("filter", config)
										for group in filter:
											stations_groups.append((group, item_name, from_mod))
			except Exception as ex:
				logging.error("Encountered an unexpected error while trying to read file {}. Traceback:\n{}\n".format(Path(file).name, traceback.format_exc()))

		end_parsing_files = datetime.now()
		diff = end_parsing_files - start_parsing_files
		logging.info("It took {} to read {} files, at a rate of {} per file".format(diff, num_of_files, diff / num_of_files))

		timer_insert_main = timer()
		timer_insert_main.t_in()
		self.cursor.executemany("INSERT INTO objects VALUES(?, ?, ?, ?, ?, ?, ?, ?)", object_list)
		self.cursor.executemany("INSERT INTO learn VALUES(?, ?, ?)", learned_list)
		self.cursor.executemany("INSERT INTO stations_groups VALUES(?, ?, ?)", stations_groups)
		diff = timer_insert_main.t_out()
		insert_num = len(object_list) + len(learned_list) + len(stations_groups)
		logging.info("It took {} to insert {} files into the database, for a rate of {} per insert".format(diff, insert_num, diff/insert_num))


		#########################
		## Create recipe lists ##
		#########################
		recipes = list(dir.glob("**/*.recipe"))
		collected_recipes = [] # I'm going to collect all of the recipes and commit them to the database in an executemany to (hopefully) speed the process up.
		recipes_groups = []
		inputs = []
		outputs = []
		for file in recipes:
			try:
				self.filename = Path(file).name
				self.reader.recipe(file)
			except Exception as ex:
				logging.error("Encountered an unexpected error while trying to read file {}. Traceback:\n{}".format(Path(file).name, traceback.format_exc()))

		in_time = datetime.now()
		self.cursor.executemany("INSERT INTO recipes VALUES(?, ?, ?)", collected_recipes)
		self.cursor.executemany("INSERT INTO recipes_groups VALUES(?, ?, ?)", recipes_groups)
		self.cursor.executemany("INSERT INTO input VALUES(?, ?, ?, ?)", inputs)
		self.cursor.executemany("INSERT INTO output VALUES(?, ?, ?, ?)", outputs)
		out_time = datetime.now()

		recipe_num = len(collected_recipes) # Used to calculate average time.
		diff = out_time - in_time # Time it took to load all recipes in.
		print("It took {} to insert all recipes for an average time of {}".format(diff, diff/recipe_num))

		self.connect.commit()

	def remove_entries_of_mod(self, mod_name="", mod_checksum=""):
		"""Removes all entries of this mod from all databases.
		:param mod_name: ID of the mod you wish to remove.
		:param mod_checksum: The checksum of the mod, if we don't have the name. This will be converted into the name using the modlist table.
		"""
		tables = ["recipes", "recipes_groups", "stations_groups", "output", "input", "objects", "learn", "modlist"] # The names of all tables in the database.

		if mod_checksum:
			mod_name = self.cursor.execute("SELECT from_mod FROM modlist WHERE checksum={}".format(mod_checksum))
		logging.debug("Attempting to remove mod {} from database...".format(mod_name))
		for table in tables:
			expr = "DELETE FROM {} WHERE from_mod=?".format(table)
			self.cursor.execute(expr, (mod_name,))
			self.connect.commit()
		logging.debug("Successfully removed {} from database".format(mod_name))

	def clear_database(self):
		"""Delete the database lmao"""
		db_file = self.data_folder + "/recipe_test.foxdb"
		if path.isfile(db_file):
			self.connect.close()
			remove(db_file)

			# Recreate DB and reconnect SQL to it
			db_file = self.data_folder + "/database.foxdb"  # Location of the database file on the PC.
			b_make_db = False  # If we detect the file missing, or detect any missing tables, create them.
			if not path.isfile(db_file):
				b_make_db = True

			self.connect = sqlite3.connect(db_file)  # Open the SQL database on the PC.
			self.cursor = self.connect.cursor()  # I don't quite understand how the cursor works, but it's the main thing used when interacting with the database.
			self.connect.create_function("REGEXP", 2, regexp)

			# If the file was detected, check if all tables are present.
			# TODO - Add this. I couldn't find a way to get the number of tables easily, so I'll do it later.
			# self.db_tables = ["recipes", "objects", "learn", "id_convert"]
			if b_make_db:
				self.create_tables()



	def search(self, table, where_value="", order="", return_column="*"):
		"""where_value
		Search database a database for results.
		Supports regex by filling out "where_value" like "REGEXP {}".

		:param table: (str) The table to select data from
		:param where_value: (array) An array of WHERE clauses, structured like ["column REGEXP 'value'", "column='value'"].
		:param order: (str) What field(s) to order the list by
		:param return_column: (str) Return only results from this column name.
		:return: (Array) All matching results
		"""

		expr = "SELECT {} FROM {}".format(return_column, table)
		if where_value:
			for index, clause in enumerate(where_value):
				if index == 0:
					expr += " WHERE {}".format(clause)
				else:
					expr += " OR {}".format(clause)

		if order != "":
			expr += " ORDER BY {}".format(order)

		self.cursor.execute(expr)
		return self.cursor.fetchall()


	def convert_id(self, id="", name=""):
		"""
		Search the 'objects' table for the converted name of this object.
		:param id: (str) The object's ID. If this is left blank, I'll assume
		:param name: (str) The object's name, to convert into an ID.
		:return: (str) if id: The matching display_name for this object. May contain colour highlighting that needs to be parsed (E.G ^orange;Table^reset;).
				(array) if name: An array of all matching IDs.
		"""
		if id != "": # Searching for ID will only match exact results. This is because I'm assuming anyone who searches an ID has the full ID.
			result = self.search("objects", where_value=["item_name='{}'".format(id)])
			try:
				return result[0][1]
			except IndexError:
				logging.warning("Search for the ID {} in objects returned nothing".format(id))
				return "?"
		else: # Searching for a display_name will always use RegEx
			where_field = "display_name REGEXP '{}'".format(name)
			result = self.search("objects", where_value=[where_field])
			all_results = []
			for value in result: # Cycle through all results...
				all_results.append(value[0]) # And store the first entry of the tuple (the item_name) in an array.
			return all_results


	def remove_colour_tags(self, text):
		type_of_var = type(text)
		if type_of_var == str:
			return re.sub(self.re_colour_tag, '', text)
		elif type_of_var == list:
			return_list = []
			for val in text:
				return_list.append(re.sub(self.re_colour_tag, '', val))
			return return_list
		else:
			logging.warning("remove_colour_tags was called with a value that is not a string or a list. Value: {}".format(text))


	# Recipe junk
	def search_recipe(self, output, input, duration, bench, from_mod):
		"""
		Search for a set of recipes that contains ALL of the input data. If a field is left blank, it is not searched for.
		:param output: (str) The display_name of one of the outputs of the recipe. This will also be the name of the recipe (I hope)
		:param input: (str) The display_name of one of the inputs of the recipe
		:param duration: (float) The time it takes for the recipe to craft.
		:param bench: (str) The display_name of the bench that this recipe can be crafted at.
		:param from_mod: (str) The friendly_name of the mod a recipe comes from
		:return: (set) The ID of any recipes that match ALL given fields.
		If some data could not be parsed: (str) "?"
		"""
		def set_merge(master_set, array):
			array = set(array)
			if master_set:
				return master_set.intersection(array)
			else: # If the master_set has already had stuff added to it.
				return array


		all_ids = set()
		# This method I'm going to do is probably very bad. I'm creating *dozens* of where_value searches, because I'm storing IDs instead of display_names.
		# Too bad!
		# What I'm doing is running a SQL search for each provided field, then comparing the intersection of all of these sets to figure out which recipes are valid candidates.
		if input:
			self.cursor.execute("SELECT recipe_name FROM input WHERE item IN (SELECT item_name FROM objects WHERE display_name REGEXP (?))", (input,))
			semi_set = []
			for row in self.cursor.fetchall():
				semi_set.append(row[0])
			all_ids = set_merge(all_ids, semi_set)
			if not all_ids: return "?"

		if output:
			self.cursor.execute("SELECT recipe_name FROM output WHERE item IN (SELECT item_name FROM objects WHERE display_name REGEXP (?))", (output,))
			semi_set = []
			for row in self.cursor.fetchall():
				semi_set.append(row[0])
			all_ids = set_merge(all_ids, semi_set)
			if not all_ids: return "?"

		if duration:
			# TODO: I need to find a way to allow for comparisons of duration (And of quantity of input/output)
			try:
				self.cursor.execute("SELECT name FROM recipes WHERE duration=(?)", (duration,))
			except sqlite3.OperationalError:
				logging.error("Failed to search for given duration in search_recipe. Duration given: {}".format(duration))
				return "?"
			semi_set = []
			for row in self.cursor.fetchall():
				semi_set.append(row[0])
			all_ids = set_merge(all_ids, semi_set)
			if not all_ids: return "?"

		if bench:
			self.cursor.execute("""SELECT recipe_name FROM recipes_groups WHERE grouping IN (
				SELECT grouping FROM stations_groups WHERE station IN (
					SELECT item_name FROM objects WHERE display_name REGEXP (?)
				)
			)""", (bench,))
			semi_set = []
			res = self.cursor.fetchall()
			for row in res:
				semi_set.append(row[0])
			all_ids = set_merge(all_ids, semi_set)
			if not all_ids: return "?"

		if from_mod:
			self.cursor.execute("SELECT name FROM recipes WHERE from_mod IN (SELECT from_mod FROM modlist WHERE friendly_name REGEXP (?))", (from_mod,))
			semi_set = []
			for row in self.cursor.fetchall():
				semi_set.append(row[0])
			all_ids = set_merge(all_ids, semi_set)
			if not all_ids: return "?"

		return all_ids

	def return_recipes_data(self, recipe_ids):
		"""
		Takes in an array of recipe ids and processes them into strings of data to display
		"""
		if recipe_ids != "?":
			return self.extract_recipe_string(self.get_recipe_information(recipe_ids))
		else:
			return

	def get_recipe_information(self, recipe_ids):
		"""
		This will search through all recipe IDs provided, and return a 3D array containing all relevant information.
		This is to be used when displaying a recipe's information, and can be provided the result from search_recipe
		:param recipe_ids: (array of strings) The ID of a recipe. This must be an exact name.
		:return: A 3D array with 6 cells per entry. The following array is for a single given recipe_id:
		[
			[
				[recipe_id, duration, from_mod], [learned_object1, learned_object2],
				[output1, output_count1, output2, output_count2], [input1, input_count1, input2, input_count2],
				[workbench_name1, workbench_name2], [grouping1, grouping2]
			]
		]
		"""
		master_array = [] # This will contain all other arrays, and be returned.

		for recipe in recipe_ids:
			sub_array = [] # The array all of the following data will be contained in.
			recipe_id = recipe

			self.cursor.execute("SELECT * FROM recipes WHERE name='{}'".format(recipe_id))
			recipes_db = self.cursor.fetchall()

			recipe_duration = recipes_db[0][1]
			recipe_mod = recipes_db[0][2]
			group1 = [recipe_id, recipe_duration, recipe_mod]

			##################
			## Learned From ##
			##################
			learned_from = []
			self.cursor.execute("SELECT display_name FROM objects WHERE item_name IN (SELECT from_object FROM learn WHERE recipe='{}')".format(recipe_id))
			for object in self.cursor.fetchall():
				learned_from.append(object[0])

			###################
			## Recipe Groups ##
			###################
			recipe_groups = []
			self.cursor.execute("SELECT grouping FROM recipes_groups WHERE recipe_name='{}'".format(recipe_id))
			raw_recipe_groups = self.cursor.fetchall()
			for group in raw_recipe_groups:
				recipe_groups.append(group[0])

			############
			## Output ##
			############
			recipe_outputs = []
			self.cursor.execute("SELECT * FROM output WHERE recipe_name='{}'".format(recipe_id))
			for output in self.cursor.fetchall():
				recipe_outputs.append(output[1])
				recipe_outputs.append(output[2])

			###########
			## Input ##
			###########
			recipe_inputs = []
			self.cursor.execute("SELECT * FROM input WHERE recipe_name='{}'".format(recipe_id))
			for input in self.cursor.fetchall():
				recipe_inputs.append(input[1])
				recipe_inputs.append(input[2])

			################
			## Created At ##
			################
			recipe_tables = []
			self.cursor.execute("""SELECT display_name FROM objects WHERE item_name IN (
				SELECT station FROM stations_groups WHERE grouping IN (
					SELECT grouping FROM recipes_groups WHERE recipe_name='{}'))""".format(recipe_id))
			# This last nested SELECT is needless. I already have stored all of the grouping values in recipe_groups. But SQLite3 has forced my hand.
			# TODO: Come back and figure out why SQLite hates me. (I probably won't because it works fine)
			all_tables = self.cursor.fetchall()
			for table in all_tables:
				recipe_tables.append(table[0])

			sub_array.append(group1)
			sub_array.append(learned_from)
			sub_array.append(recipe_outputs)
			sub_array.append(recipe_inputs)
			sub_array.append(recipe_tables)
			sub_array.append(recipe_groups)
			master_array.append(sub_array)

		return master_array

	def extract_recipe_string(self, recipe_data):
		"""Create a string about all contained recipes.
		Should be provided with the 3D array output by get_recipe_string
		:param recipe_data: Should be provided with a 3D array output by get_recipe_information"""

		print_values = []
		for recipe in recipe_data:
			item_id = recipe[0][0] # The ID of the output item.
			duration = recipe[0][1] # How long it takes to craft
			from_mod = recipe[0][2] # Which mod this recipe came from

			# Which objects you can pick up to learn this recipe.
			learned_from = ""
			list_size = len(recipe[1])
			for index, learned in enumerate(recipe[1]):
				if index == 0:
					learned_from = learned
				elif index == (list_size - 1):  # Last entry of the list
					learned_from += " and {}".format(learned)
				else:
					learned_from += ", {}".format(learned)

			# What this recipe creates
			output = ""
			recipe_name = ""
			num_of_outputs = int(len(recipe[2]) / 2)  # This is divided by two because there will always be 2 entries per output, count and item
			for index in range(num_of_outputs):
				list_pos = index * 2
				object_name = self.remove_colour_tags(self.convert_id(id=recipe[2][list_pos]))
				object_count = recipe[2][list_pos + 1]

				if index == 0:
					recipe_name = "{}".format(object_name)
					output = "{} (x{})".format(object_name, object_count)
				else:
					output += ", {} (x{})".format(object_name, object_count)
					recipe_name += "{}".format(object_name)  # Hopefully this never happens.

			# What items are required by this recipe
			inputval = ""
			num_of_inputs = int(len(recipe[3]) / 2)  # This is divided by two because there will always be 2 entries per input, count and item
			for index in range(num_of_inputs):
				list_pos = index * 2
				object_name = self.remove_colour_tags(self.convert_id(id=recipe[3][list_pos]))
				object_count = recipe[3][list_pos + 1]

				if index == 0:
					inputval = "{} (x{})".format(object_name, object_count)
				else:
					inputval += ", {} (x{})".format(object_name, object_count)

			# Any benches this crafting recipe can be found at.
			benches = ""
			list_size = len(recipe[4]) # Used to check what position in the list of benches we're in, so we can change the verbal structure of the sentence.
			for index, bench_name in enumerate(recipe[4]):
				bench_name_clean = self.remove_colour_tags(bench_name)
				if index == 0:
					benches = "{}".format(bench_name_clean)
				elif index == (list_size - 1):
					benches += " and {}".format(bench_name_clean)
				else:
					benches += ", {}".format(bench_name_clean)

			# The crafting groups that this recipe is available in.
			groups = ""
			list_size = len(recipe[5])
			for index, group_name in enumerate(recipe[5]):
				if index == 0:
					groups = "{}".format(group_name)
				else:
					groups += ", {}".format(group_name)

			print_value = """Recipe name: {}
	Crafted at: {}
	Crafted with: {}
	Creates: {}
	Learned from: {}
	This recipe takes {}s to craft.
	
	Meta info:
	Recipe groups: {}
	Item ID: {}
	From Mod: {}\n\n""".format(recipe_name, benches, inputval, output, learned_from, duration, groups, item_id, from_mod)
			print_values.append(print_value)

		return print_values








	# Private functions. Things that will only be used within this class.

	# Remove instanecs of filename from this.
	def create_group_list(self, name, from_mod, obj, directory):
		"""
		Used to parse an object and check if it contains elements of a crafting table. If so, return information required for a group_list entry.
		:param name: (str) Name of this object.
		:param from_mod: (str)
		:param obj: (str) The json you're attemping to check.
		:param directory: The directory of the unpacked files.
		"""
		all_groups = []
		interact_data = self.json_get("interactData", obj)
		if interact_data != "?":
			groups = ""
			# Check for filter.
			filter = self.json_get("filter", interact_data)
			if filter != "?":
				for group in filter:
					all_groups.append((group, name, from_mod))
			else:
				# Check config file
				config_location = str(directory) + self.json_get("config", interact_data)
				config = self.read_json(config_location)
				if config != "?":
					filter = self.json_get("filter", config)
					for group in filter:
						all_groups.append((group, name, from_mod))
				else:
					logging.warning("Cannot read config file at {}".format(config_location))
					all_groups.append(("?", name, from_mod))
		else:
			all_groups.append(("?", name, from_mod))
		return all_groups

	def read_json(self, file_path):
		"""
		Attempts to read the contents of a JSON file. As Starbound allows for comments in its files, I need to be able to delete these comments if they arise.
		:param file_path: (str) The location of the file on disk you wish to read OR a string of the full file.
		:return: Returns a dictionary of the JSON file, or None if the operation failed.
		"""
		with open(file_path) as file:
			try:
				data = json.load(file, strict=False)
				return data
			except json.decoder.JSONDecodeError:
				#logging.debug("Erroneous JSON code in {}, attempting to fix...".format(Path(file_path).name))
				file.seek(0)  # We've already read the file once, so reset the seek.
				new_file = file.read()  # Convert the file to a string so we can run functions on it.

				# Search for inline comments.
				new_file = re.sub(self.re_line_comment, '', new_file)

				# Search for block comments.
				new_file = re.sub(self.re_block_comment, '', new_file)

				# Try to read the string again after all comments have been removed.
				try:
					data = json.loads(new_file, strict=False)  # Changed to loads with an s as we're reading a string, not a file.
					return data
				except Exception as ex:
					logging.warning("Cannot load file JSON file {}, error {}.".format(Path(file_path).name, ex))
					data = None
					return data
			except Exception as ex:
				logging.error("Unknown error happened while attempting to decode {}\n{}".format(Path(file_path).name, ex))

	def reset(self):
		"""Defines and or resets all of the self. variables I will be using."""
		self.mod_files = []  # The directories of all mods the user has with an unrecognized checksum.
		self.mod_checksums = []  # All of the file checksums of the mods, essentially their identification. We'll add these to modlist.fox when we're done.
		self.mod_names = []  # Will contain all of the names in the metadata.
		self.undetected_checksums = set({})  # Any checksums that were not found. These will be mods we'll need to search for in case they have been updated.
		self.found_mods = set({})  # These are all of the mod checksums from the files that we DO recognize.
		self.indexed_checksums = []  # All checksums in modlist.fox
		self.indexed_friendly_names = []  # All mod names in modlist.fox. The index in this list should relate to the checksum of self.indexed_checksums
		self.lost_mods = []  # A list of the names of all mods that could not be found. We'll use this name to remove any entries that were added by this mod.

		self.b_new_mods = False  # This will evaluate if there's a new mod detected. New mods should be pulled from self.mod_files
		self.b_lost_mods = False  # Whether there are mods that used to be on here, but are no longer detected.

		self.filename = "" # The name of the file that we're currently parsing.

	def remove_staged(self, checksum):
		"""Removes the folder and all files of a staged checksum. Also removes the checksum from the database.
		:param checksum: The checksum corresponding to the name of the folder."""
		folder = self.unpack_location + "/{}".format(checksum)
		if Path(folder).exists():
			rmtree(folder)
			expr = "DELETE FROM unpacked_files WHERE checksum={}".format(checksum)
			self.cursor.execute(expr)
			self.connect.commit()
		else:
			logging.warning("Provided checksum {} does not exist, cannot remove from files.\nTrackback:\n{}".format(folder, traceback.format_exc()))

	def create_tables(self):
		### CREATE TABLES ###
		self.cursor.execute("begin")
		# Notes about database:
		# Every entry should always contain an accurate "from_mod" field.
		# Any place that would have to store multiple entries (such as recipe input fields), the values are put into a different database, and connected by name. See diagram for relationships.

		# Objects table
		self.cursor.execute("""CREATE TABLE objects (
			item_name TEXT,
			display_name TEXT,
			category TEXT,
			price INTEGER,
			two_handed INTEGER,
			rarity TEXT,
			description TEXT,
			from_mod TEXT
			)""")

		# Recipes table
		self.cursor.execute("""CREATE TABLE recipes (
			name TEXT,
			duration REAL,
			from_mod TEXT
			)""")

		# Learning table
		self.cursor.execute("""CREATE TABLE learn (
			from_object TEXT,
			recipe TEXT,
			from_mod TEXT
			)""")

		# The following four tables are essentially used as arrays in other tables. SQLite3 doesn't support arrays as a datatype.
		# Input table
		self.cursor.execute("""CREATE TABLE input (
			recipe_name TEXT,
			item TEXT,
			count INTEGER,
			from_mod TEXT
			)""")

		# Output table
		self.cursor.execute("""CREATE TABLE output (
			recipe_name TEXT,
			item TEXT,
			count INTEGER,
			from_mod TEXT
			)""")

		# station_groups table
		self.cursor.execute("""CREATE TABLE stations_groups (
			grouping TEXT,
			station TEXT,
			from_mod TEXT
			)""")

		# recipes_groups table
		self.cursor.execute("""CREATE TABLE recipes_groups (
			grouping TEXT,
			recipe_name TEXT,
			from_mod TEXT
			)""")

		# Modlist table.
		self.cursor.execute("""CREATE TABLE modlist (
			checksum TEXT,
			from_mod TEXT,
			friendly_name TEXT,
			author TEXT,
			version TEXT
			)""")

		# Staged unpack files. These are files that have been unpacked, but **not** parsed for data yet. The checksum is the name of their folder.
		self.cursor.execute("""CREATE TABLE unpacked_files (
			checksum TEXT
			)""")

		self.cursor.execute("commit")

	def json_get(self, key, data, error_on_fail=True, error_message=""):
		"""
		Provides generic error handling when retrieving a key:value from a dictionary.
		:param key: (str) The key that you're trying to read.
		:param data: (dict) The dictionary you're trying to read from.
		:param error_on_fail: (bool) Whether it should print an error message if this operation fails
		:param error_message: (str) The message that should be printed if this operation fails.
		"""
		try:
			val = data[key]
		except KeyError:
			val = "?"
			if error_on_fail:
				if error_message:
					logging.warning(error_message)
				else:
					logging.info("File {} has no key {}.".format(self.filename, key))
		except TypeError:
			val = "config"
			if error_on_fail:
				logging.info("File {} seems to be interactData for a config.".format(self.filename))

		return val



def regexp(expr, item):
	reg = re.compile(expr, re.I) # This will make ALL searches case insensitive. Too bad!
	return reg.search(item) is not None


def generate_checksum(file_path):
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


# woo line 1000 (right now). arix is gayrix
