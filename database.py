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




class timer():
	"""Very basic object that is used to track how much time something took."""
	def t_in(self):
		self.time_in = datetime.now()
	def t_out(self):
		self.time_out = datetime.now()
		return self.time_out - self.time_in

class database():

	def __init__(self):
		self.program_folder = str(Path.cwd()) # The location of this program's master folder.
		self.data_folder = "{}/data".format(self.program_folder)
		self.unpack_location = "{}/data/unpack".format(self.program_folder)  # Location where files will be unpacked to (string)
		self.recipe_id_count = "{}/data/r_id.fox".format(self.program_folder) # This will store which ID we're up to in recipes. This is required to keep track of which values goes to which recipe.
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

		self.re_line_comment = re.compile(r'//.*') # This can find all line comments in JSON (//Text after this). TODO: I need to name sure this DOESN'T delete comments within keys/values. We'll have issues if it does.
		self.re_block_comment = re.compile(r'(/\*)(.|\n)+?(\*/)') # This is used to search a JSON file for block comments.
		self.re_colour_tag = re.compile(r'\^.*?;') # This will find colour tags in the names of things, E.G ^orange;nameofobject^reset;
		var = self.program_folder.replace("\\", "/")
		self.re_file_path = re.compile(r'(?<={})(.*)'.format(var))

		# Declares many more variables that may need to be reset at times.
		self.reset()

	# Process for updating the database:
	# index_mods > prime_files > parse_files
	# At each point in this process, it is stopped to allow user input on whether to continue now or later.
	# I also allow a "do all" option so the user can just set it to work and forget about it.

	# Database management functions.
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
		unexpected_error_msg = "Encountered an unexpected error while trying to read file {} from the mod {}.\n{}"
		object_list = []
		learned_list = []
		# TODO: Figure out why "peacekeeper1" isn't being indexed.

		####################
		## Create modlist ##
		####################
		# TODO: Apparently the metadata file is optional, so I need to find a way to deal with that in the event that a mod doesn't include it. Likely I'll just use the checksum as a backup.
		meta = str(dir) + "/_metadata"
		fields = ["name", "friendlyName", "author", "version"] # This will contain all fields that can be handled in a similar/same way. Other fields may be done manually.
		values = [] # A generic field we'll store things in temporarily

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
		self.from_mod = values[0] # This will be used by following fields to identify which mod this came from.

		self.cursor.execute("INSERT INTO modlist VALUES (?, ?, ?, ?, ?)", (checksum, values[0], values[1], values[2], values[3]))


		################
		## BULK PARSE ##
		################
		# Surgical imprecision.
		# Just here temporarily until I can create manual parsing for every file type.

		# List of all file extensions we need to parse for useful data.
		extensions = ["liqitem", "matitem", "chest", "legs", "head", "activeitem", "augment", "back", "beamaxe", "currency", "flashlight", "harvestingtool", "inspectiontool", "instrument", "item", "miningtool", "objectdisabled", "painttool", "thrownitem", "tillingtool", "wiretool"]
		all_files = []

		for exten in extensions:
			all_files += list(dir.glob("**/*.{}".format(exten)))
		num_of_files = len(all_files)

		start_parsing_files = datetime.now()
		# Search through all decompiled files.
		for file in all_files:
			self.filename = Path(file).name
			try:
				data = self.get_generic(file)
				object_list.append(data[1])
				for learn in data[2]:
					learned_list.append(learn)
			except Exception as ex:
				logging.error("Encountered an unexpected error while trying to read file {}\n{}\n".format(Path(file).name, traceback.format_exc()))

		#############
		## Objects ##
		#############
		objects = list(dir.glob("**/*.object"))
		stations_groups = []
		for file in objects:
			self.filename = Path(file).name
			try:
				data = self.read_object_file(file)
				for object in data[0]:
					object_list.append(object)
				for group in data[1]:
					stations_groups.append(group)
				for learn in data[2]:
					learned_list.append(learn)
			except Exception:
				logging.error(unexpected_error_msg.format(self.filename, self.from_mod, traceback.format_exc()))



		################
		## Consumable ##
		################
		consumables = list(dir.glob("**/*.consumable"))
		my_object_list = [] # Contains the bulk of information about an object.
		consumable_list = []
		for file in consumables:
			self.filename = Path(file).name
			try:
				data = self.read_consumable_file(file)
				my_object_list.append(data[0])
				consumable_list.append(data[1])
				for val in data[2]:
					learned_list.append(val)
			except Exception:
				logging.error(unexpected_error_msg.format(self.filename, self.from_mod, traceback.format_exc()))

		object_list.extend(my_object_list)

		#############
		## Recipes ##
		#############
		# Get recipe count ID
		try:
			with open(self.recipe_id_count, "r") as f:
				recipe_count = int(f.read())
		except FileNotFoundError:
			logging.warning("Recipe ID count file could not be found. If the database isn't empty, this might cause ID overlapping.")
			recipe_count = 0
		except ValueError:
			logging.warning("Recipe Count cannot be read, was likely formatted incorrectly. If the database isn't empty, this might cause ID overlapping.")
			recipe_count = 0

		# Read from files
		recipes = list(dir.glob("**/*.recipe"))
		collected_recipes = []  # I'm going to collect all of the recipes and commit them to the database in an executemany to (hopefully) speed the process up.
		recipes_groups = []
		inputs = []
		for file in recipes:
			self.filename = Path(file).name
			try:
				data = self.read_recipe_file(file, recipe_count)
				# Assign received data.
				recipe_count += 1
				collected_recipes.append(data[0])
				for input_field in data[1]:
					inputs.append(input_field)
				for group_field in data[2]:
					recipes_groups.append(group_field)
			except Exception:
				logging.error(unexpected_error_msg.format(self.filename, self.from_mod, traceback.format_exc()))


		# Add collected data to the database.
		in_time = datetime.now()

		# General
		#for entry in object_list:
		#	print(entry)
		#	self.cursor.execute("INSERT INTO things VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)", entry)
		self.cursor.executemany("INSERT INTO things VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)", object_list)
		self.cursor.executemany("INSERT INTO learn VALUES(?, ?, ?)", learned_list)
		# Recipes
		self.cursor.executemany("INSERT INTO recipes VALUES(?, ?, ?, ?, ?)", collected_recipes)
		self.cursor.executemany("INSERT INTO input VALUES(?, ?, ?, ?)", inputs)
		self.cursor.executemany("INSERT INTO recipes_groups VALUES(?, ?, ?)", recipes_groups)
		# Consumables
		self.cursor.executemany("INSERT INTO consumables VALUES(?, ?, ?, ?, ?)", consumable_list)
		# Objects
		self.cursor.executemany("INSERT INTO stations_groups VALUES(?, ?, ?)", stations_groups)

		self.connect.commit()

		out_time = datetime.now()

		with open(self.recipe_id_count, "w") as f:
			f.write(str(recipe_count))

		# Report performance
		recipe_num = len(collected_recipes) # Used to calculate average time.
		diff = out_time - in_time # Time it took to load all recipes in.
		try:
			print("It took {} to insert all recipes for an average time of {}".format(diff, diff/recipe_num))
		except ZeroDivisionError:
			pass

		self.connect.commit()

	def remove_entries_of_mod(self, mod_name="", mod_checksum=""):
		"""Removes all entries of this mod from all databases.
		:param mod_name: ID of the mod you wish to remove.
		:param mod_checksum: The checksum of the mod, if we don't have the name. This will be converted into the name using the modlist table.
		"""
		tables = ["recipes", "recipes_groups", "stations_groups", "output", "input", "things", "learn", "modlist"] # The names of all tables in the database.

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
		db_file = self.data_folder + "/database.foxdb"
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

		if path.isfile(self.recipe_id_count):
			remove(self.recipe_id_count)




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
		Search the 'things' table for the converted name of this object.
		:param id: (str) The object's ID. If this is left blank, I'll assume
		:param name: (str) The object's name, to convert into an ID.
		:return: (str) if id: The matching display_name for this object. May contain colour highlighting that needs to be parsed (E.G ^orange;Table^reset;).
				(array) if name: An array of all matching IDs.
		"""
		if id != "": # Searching for ID will only match exact results. This is because I'm assuming those who search an ID has the full ID (likely via an automated process).
			result = self.cursor.execute("SELECT display_name FROM things WHERE item_name=(?)", (id,)).fetchall()
			try:
				return result[0][0]
			except IndexError:
				logging.warning("Search for the ID {} in things returned nothing".format(id))
				return id
		else: # Searching for a display_name will always use RegEx
			result = self.cursor.execute("SELECT item_name FROM things WHERE display_name REGEXP (?)", (name,))
			all_results = []
			for value in result: # Cycle through all results...
				all_results.append(value[0]) # And store the first entry of the tuple (the item_name) in an array.
			return all_results

	def convert_recipe_id(self, item_name):
		"""Takes the name of an output of a recipe, and returns all IDs that output it."""
		return self.cursor.execute("SELECT recipe_id FROM recipes WHERE name=(?)", (item_name,)).fetchall()

	def convert_mod_id(self, mod_id="", mod_friendly_name=""):
		"""Will convert mod ID to friendly name, or friendly name to mod ID"""
		try:
			if mod_id:
				return self.cursor.execute("SELECT friendly_name FROM modlist WHERE from_mod=(?)", (mod_id,)).fetchall()[0][0]
			elif mod_friendly_name:
				return self.cursor.execute("SELECT from_mod FROM modlist WHERE friendly_name=(?)", (mod_friendly_name,)).fetchall()[0][0]
		except:
			return mod_id + mod_friendly_name

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


	# File parsing presets
	def get_generic(self, filepath):
		"""Get any generic data required to fill the 'things' and 'learn' tables.
		:param read_data: A file that has been parsed by read_json
		:return: A multidimensional array structured as so:
		[
			(READ_DATA) # So I don't need to read the data multiple times. For performance.
			# 'things' data
			(name, display_name, category, price, rarity, description, filepath, inventory_icon, from_mod),
			[
				# 'learn' data
				(from_object, recipe_name, from_mod),
				(from_object, recipe_name, from_mod)
			]
		]
		"""
		read_data = self.read_json(str(filepath))

		object_name = self.json_get("objectName", read_data, error_on_fail=False, default="")
		if not object_name:
			object_name = self.json_get("itemName", read_data, error_level=logging.error)
		display_name = self.json_get("shortdescription", read_data, error_level=logging.warning, default="UNKNOWN")
		category = self.json_get("category", read_data, error_level=logging.warning, default="Not set :(")
		price = self.json_get("price", read_data, error_level=logging.info, default=-1)
		rarity = self.json_get("rarity", read_data, default="D: Not set")
		description = self.json_get("description", read_data, default="Non-descriptive description (not set >:c)")
		inventory_icon = self.json_get("inventoryIcon", read_data, error_level=logging.info, default="icon.png")
		if not isinstance(inventory_icon, str): # This is temporary, it's just that some files store it in a weird way I can't be bothered with rn
			inventory_icon = "icon.png"
		try:
			location = re.search(self.re_file_path, str(filepath)).group(0)
		except AttributeError:
			location = "unknown"

		object_data = (object_name, display_name, category, price, rarity, description, location, inventory_icon, self.from_mod)

		# Learned blueprints
		my_learned = []
		learned_blueprints = self.json_get("learnBlueprintsOnPickup", read_data, error_on_fail=False, default="")
		for blueprint in learned_blueprints:
			my_learned.append((object_name, blueprint, self.from_mod))

		return [read_data, object_data, my_learned]

	def read_object_file(self, filepath):
		"""

		:param filepath: The location on disk of the file to read.
		:return: A multidimensional array with data formatted like so:
		(
			[
				# 'things' data
				(name, display_name, category, price, rarity, description, filepath, inventory_icon, from_mod),
				(name, display_name, category, price, rarity, description, filepath, inventory_icon, from_mod)
			],
			[
				'stations_groups' data
				(group, recipe_output, from_mod),
				(group, recipe_output, from_mod)
			],
			[
				'learn' data
				(from_object, recipe_name, from_mod),
				(from_object, recipe_name, from_mod)
			]
		)
		"""
		my_objects = []
		my_groups = []
		my_learned = []

		generic = self.get_generic(filepath)
		read_data = generic[0]
		object_data = generic[1]
		my_learned.extend(generic[2])

		# Check for upgrade stages
		upgrade_stages = self.json_get("upgradeStages", read_data, error_on_fail=False, default="")
		if upgrade_stages:
			# Pull the object data from the generic data to reference for upgrade stages.
			object_name = object_data[0]
			display_name = object_data[1]
			category = object_data[2]
			price = object_data[3]
			rarity = object_data[4]
			description = object_data[5]
			location = object_data[7]
			inventory_icon = object_data[6]


			for stage in upgrade_stages:
				# Create object
				stage_name = self.json_get("animationState", stage, error_level=logging.error, default=object_name)

				item_params = self.json_get("itemSpawnParameters", stage, error_level=logging.error) # For now I will let this scream loudly so that I can see what this looks like in code.
				stage_display_name = self.json_get("shortdescription", item_params, error_on_fail=False, default=display_name)
				stage_category = self.json_get("category", item_params, error_on_fail=False, default=category) # Not sure if it can redefine this anyway.
				stage_price = self.json_get("price", item_params, error_on_fail=False, default=price)
				stage_rarity = self.json_get("rarity", item_params, error_on_fail=False, default=rarity)
				stage_description = self.json_get("description", item_params, error_on_fail=False, default=description)
				stage_inventory_icon = self.json_get("inventoryIcon", item_params, error_on_fail=False, default=inventory_icon)

				my_objects.append((stage_name, stage_display_name, stage_category, stage_price, stage_rarity, stage_description, location, stage_inventory_icon, self.from_mod))

				# Create groups
				interact_data = self.json_get("interactData", stage, error_level=logging.error)
				filters = self.json_get("filter", interact_data, error_on_fail=False, default="")
				if filters:
					for filter in filters:
						my_groups.append((filter, stage_name, self.from_mod))
				#else: # Search the config.


				# Create learning table
				learnonpickup = self.json_get("learnBlueprintsOnPickup", stage, error_on_fail=False, default="")
				for recipe in learnonpickup:
					my_learned.append((stage_name, recipe, self.from_mod))

				# TODO add racial descriptions here
		else:
			my_objects.append(object_data)
			object_name = object_data[0]

			# Grouping data. For crafting tables only.
			interactData = self.json_get("interactData", read_data, error_on_fail=False, default="")
			if interactData:
				try:
					filters = self.json_get("filter", interactData, error_level=logging.info, default="") # TODO need to change this error handling.
					if filters == "":
						raise KeyError # This is just temporary, till I change error handling.
				except TypeError: # This might happen in the event that interactData stores the dir of a config.
					pass
				except KeyError:
					pass
				else:
					for filter in filters:
						my_groups.append((filter, object_name, self.from_mod))

		return [my_objects, my_groups, my_learned]

	def read_recipe_file(self, filepath, recipe_id):
		"""
		:param filepath: The file that needs to be read
		:param recipe_id: The ID this recipe will have.
		:return: Multidimensional array structured like the following:
		[
			('recipename', 'recipe_output', quantity, duration, 'from_mod'),
			[
				('recipename', 'recipe_input', count, 'from_mod'), (...)
			],
			[
				('crafting_group', 'recipename', 'from_mod'), (...)
			]
		]
		"""
		recipes_groups = []
		inputs = []
		read_data = self.read_json(str(filepath))

		#################
		## Get outputs ##
		#################
		output_field = self.json_get("output", read_data, error_level=logging.error)
		outputs_name = self.json_get("item", output_field, error_on_fail=False)
		if outputs_name == "?":
			# This will run if "item" is not specified.
			err_msg = "File {} from mod {} has a faulty 'output' field. It might be storing its data as an array of key:values rather than just 2 key:values.".format(self.filename, self.from_mod)
			self.outputs_name = self.json_get("name", output_field, error_level=logging.error, error_message=err_msg)
		outputs_count = self.json_get("count", output_field, error_on_fail=False, default=1)

		################
		## Get inputs ##
		################
		input_field = self.json_get("input", read_data, error_level=logging.error)
		if len(input_field) < 1:
			logging.error("File {} from mod {} has an empty input field".format(self.filename, self.from_mod))
		for i in input_field: # NOTE: I'm not sure if it's possible for an input to store a dictionary instead of an array of dictionaries. For now I will assume it cannot.
			input_name = self.json_get("item", i, error_on_fail=False)
			if input_name == "?":
				input_name = self.json_get("name", i, error_level=logging.error,
					error_message="File {} from mod {} seems to have a faulty input field".format(self.filename, self.from_mod))
			input_count = self.json_get("count", i, default=1)
			inputs.append((recipe_id, input_name, input_count, self.from_mod))

		################
		## Get groups ##
		################
		groups = self.json_get("groups", read_data)
		for group in groups:
			recipes_groups.append((group, recipe_id, self.from_mod))

		# Get duration
		duration = self.json_get("duration", read_data, default=0.1, error_on_fail=False) # Thank you to Pixelflame5826#1645 on Discord for helping me out here <3

		collected_recipe = (outputs_name, recipe_id, outputs_count, duration, self.from_mod)
		return [collected_recipe, inputs, recipes_groups]
	
	def read_consumable_file(self, filepath):
		"""Parses a .consumable file, to be used within the database.
		:param filepath: The location on disk of the file to read.
		:return: A multidimensional array with data formatted like so:
		(
			(name, display_name, category, price, rarity, description, filepath, inventory_icon, from_mod),
			(name, effects, rotting_mult, max_stack, food_value, from_mod),
			[
				(name, recipe_output, from_mod),
				(name, recipe_output, from_mod)
			}
		)
		"""
		generic = self.get_generic(filepath)

		read_data = generic[0]
		object_data = generic[1]
		learned_data = generic[2]

		read_data = self.read_json(str(filepath))
		object_name = object_data[0]

		# Consumable data
		food_value = self.json_get("foodValue", read_data, error_level=logging.info, default=-1)
		max_stack = self.json_get("maxStack", read_data, error_level=logging.info, default=-1)
		rotting_mult = self.json_get("rottingMultiplier", read_data, error_level=logging.info, default=-1)

		consumable_data = (object_name, rotting_mult, max_stack, food_value, self.from_mod)

		return [object_data, consumable_data, learned_data]






	# Recipe functions
	# Process for getting a recipe from a search:
	# search_recipe > get_recipe_information > extract_recipe_string
	def search_recipe(self, output, input, duration, bench, from_mod, display_name_search=True):
		"""
		Search for a set of recipes that contains ALL of the input data. If a field is left blank, it is not searched for.
		:param output: (str) The display_name of one of the outputs of the recipe. This will also be the name of the recipe (I hope)
		:param input: (str) The display_name of one of the inputs of the recipe
		:param duration: (float) The time it takes for the recipe to craft.
		:param bench: (str) The display_name of the bench that this recipe can be crafted at.
		:param from_mod: (str) The friendly_name of the mod a recipe comes from
		:param display_name_search: (bool) If it should convert from display name to itemID.
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
		if output:
			if display_name_search:
				self.cursor.execute("SELECT recipe_id FROM recipes WHERE name IN (SELECT item_name FROM things WHERE display_name REGEXP (?))", (output,))
			else:
				self.cursor.execute("SELECT recipe_id FROM recipes WHERE name REGEXP (?)", (output,))

			semi_set = []
			for row in self.cursor.fetchall():
				semi_set.append(row[0])
			all_ids = set_merge(all_ids, semi_set)
			if not all_ids: return "?"

		if input:
			if display_name_search:
				self.cursor.execute("SELECT recipe_id FROM input WHERE item IN (SELECT item_name FROM things WHERE display_name REGEXP (?))", (input,))
			else:
				self.cursor.execute("SELECT recipe_id FROM input WHERE item REGEXP (?)", (input,))

			semi_set = []
			for row in self.cursor.fetchall(): # Since we're searching the input table, we'll get multiple of the same ID.
				semi_set.append(row[0])
			all_ids = set_merge(all_ids, semi_set)
			if not all_ids: return "?"

		if duration:
			# TODO: I need to find a way to allow for comparisons of duration (And of quantity of input/output)
			try:
				self.cursor.execute("SELECT recipe_id FROM recipes WHERE duration=(?)", (duration,))
			except sqlite3.OperationalError:
				logging.error("Failed to search for given duration in search_recipe. Duration given: {}".format(duration))
				return "?"
			semi_set = []
			for row in self.cursor.fetchall():
				semi_set.append(row[0])
			all_ids = set_merge(all_ids, semi_set)
			if not all_ids: return "?"

		if bench:
			if display_name_search:
				self.cursor.execute("""SELECT recipe_id FROM recipes_groups WHERE grouping IN (
					SELECT grouping FROM stations_groups WHERE station IN (
						SELECT item_name FROM things WHERE display_name REGEXP (?)
					)
				)""", (bench,))
			else:
				self.cursor.execute("""SELECT recipe_id FROM recipes_groups WHERE grouping IN (
					SELECT grouping FROM stations_groups WHERE station REGEXP (?)
				)""", (bench,))
			semi_set = []
			res = self.cursor.fetchall()
			for row in res:
				semi_set.append(row[0])
			all_ids = set_merge(all_ids, semi_set)
			if not all_ids: return "?"

		if from_mod:
			if display_name_search:
				self.cursor.execute("SELECT recipe_id FROM recipes WHERE from_mod IN (SELECT from_mod FROM modlist WHERE friendly_name REGEXP (?))", (from_mod,))
			else:
				self.cursor.execute("SELECT recipe_id FROM recipes WHERE from_mod REGEXP (?)", (from_mod,))
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
		:return: A multidimensional array with 6 "cells" per entry recipe_id. The following array is for a single given recipe_id:
		[
			[
				[name, recipe_id, count, duration, from_mod], [learned_object1, learned_object2],
				[input1, input_count1, input2, input_count2],
				[workbench_name1, workbench_name2], [grouping1, grouping2]
			]
		]
		"""
		master_array = [] # This will contain all other arrays, and be returned.

		for recipe in recipe_ids:
			sub_array = [] # The array all of the following data will be contained in.
			recipe_id = recipe

			self.cursor.execute("SELECT * FROM recipes WHERE recipe_id=(?)", (recipe_id,))
			recipes_db = self.cursor.fetchall() # Hopefully there should only be one result here.

			recipe_name = recipes_db[0][0]
			recipe_id = recipes_db[0][1]
			recipe_count = recipes_db[0][2]
			recipe_duration = recipes_db[0][3]
			recipe_mod = recipes_db[0][4]
			group1 = [recipe_name, recipe_id, recipe_count, recipe_duration, recipe_mod]

			##################
			## Learned From ##
			##################
			learned_from = []
			self.cursor.execute("SELECT from_object FROM learn WHERE recipe_name=(?)", (recipe_name,))
			for object in self.cursor.fetchall():
				learned_from.append(object[0])

			###################
			## Recipe Groups ##
			###################
			recipe_groups = []
			self.cursor.execute("SELECT grouping FROM recipes_groups WHERE recipe_id=(?)", (recipe_id,))
			raw_recipe_groups = self.cursor.fetchall()
			for group in raw_recipe_groups:
				recipe_groups.append(group[0])

			###########
			## Input ##
			###########
			recipe_inputs = []
			self.cursor.execute("SELECT * FROM input WHERE recipe_id=(?)", (recipe_id,))
			for input in self.cursor.fetchall():
				recipe_inputs.append(input[1])
				recipe_inputs.append(input[2])

			################
			## Created At ##
			################
			recipe_tables = []
			self.cursor.execute("""SELECT station FROM stations_groups WHERE grouping IN (SELECT grouping FROM recipes_groups WHERE recipe_id=(?))""", (recipe_id,))
			all_tables = self.cursor.fetchall()
			for table in all_tables:
				recipe_tables.append(table[0])

			sub_array.append(group1)
			sub_array.append(learned_from)
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
			output_name = recipe[0][0] # The name of the object that is output.
			output_display_name = self.remove_colour_tags(self.convert_id(id=output_name))
			recipe_id = recipe[0][1] # The ID of the recipe. Used to search for data about it.
			output_count = recipe[0][2] # How many of this object the recipe outputs.
			duration = recipe[0][3]
			from_mod = recipe[0][4]
			mod_friendly = self.convert_mod_id(from_mod)

			# Which things you can pick up to learn this recipe.
			learned_from = ""
			list_size = len(recipe[1])
			for index, learned in enumerate(recipe[1]):
				display_name = self.remove_colour_tags(self.convert_id(id=learned))
				if index == 0:
					learned_from = display_name
				elif index == (list_size - 1):  # Last entry of the list
					learned_from += " and {}".format(display_name)
				else:
					learned_from += ", {}".format(display_name)

			# What items are required by this recipe
			inputval = ""
			num_of_inputs = int(len(recipe[2]) / 2)  # This is divided by two because there will always be 2 entries per input, count and item
			for index in range(num_of_inputs):
				list_pos = index * 2

				object_name = recipe[2][list_pos]
				display_name = self.remove_colour_tags(self.convert_id(object_name))
				object_count = recipe[2][list_pos + 1]

				if index == 0:
					inputval = "{} (x{})".format(display_name, object_count)
				else:
					inputval += ", {} (x{})".format(display_name, object_count)

			# Any benches this crafting recipe can be found at.
			benches = ""
			list_size = len(recipe[3]) # Used to check what position in the list of benches we're in, so we can change the verbal structure of the sentence.
			for index, bench_name in enumerate(recipe[3]):
				display_name = self.remove_colour_tags(self.convert_id(bench_name))
				if index == 0:
					benches = "{}".format(display_name)
				elif index == (list_size - 1):
					benches += " and {}".format(display_name)
				else:
					benches += ", {}".format(display_name)

			# The crafting groups that this recipe is available in.
			groups = ""
			list_size = len(recipe[4])
			for index, group_name in enumerate(recipe[4]):
				if index == 0:
					groups = "{}".format(group_name)
				else:
					groups += ", {}".format(group_name)

			print_value = "Recipe name: {0}\n"\
				"Crafted at: {1}\n"\
				"Crafted with: {2}\n"\
				"Creates: {3} (x{4})\n"\
				"Learned from: {5}\n"\
				"This recipe takes {6}s to craft.\n\n"\
				"Meta info:\n"\
				"Recipe groups: {7}\n"\
				"Item ID: {8}\n"\
				"From Mod: {9} aka {10}\n"\
				"==========================================\n".format(output_display_name, benches, inputval, output_display_name, output_count, learned_from, duration, groups, output_name, mod_friendly, from_mod)
			print_values.append(print_value)

		return print_values








	# Private functions. Things that will only be used within this class.

	# Remove instanecs of filename from this.
	def create_group_list(self, name, obj, directory):
		"""
		Used to parse an object and check if it contains elements of a crafting table. If so, return information required for a group_list entry.
		:param name: (str) Name of this object.
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
					all_groups.append((group, name, self.from_mod))
			else:
				# Check config file
				config_location = str(directory) + self.json_get("config", interact_data)
				config = self.read_json(config_location)
				if config != "?":
					filter = self.json_get("filter", config)
					for group in filter:
						all_groups.append((group, name, self.from_mod))
				else:
					logging.warning("Cannot read config file at {}".format(config_location))
					all_groups.append(("?", name, self.from_mod))
		else:
			all_groups.append(("?", name, self.from_mod))
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
		self.from_mod = "" # The name of the mod we're currently parsing.

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
			logging.warning("Provided checksum {} does not exist, cannot remove from files.\n{}".format(folder, traceback.format_exc()))

	def create_tables(self):
		### CREATE TABLES ###
		self.cursor.execute("begin")
		# Notes about database:
		# Every entry should always contain an accurate "from_mod" field.
		# Any place that would have to store multiple entries (such as recipe input fields), the values are put into a different database, and connected by name. See diagram for relationships.

		# Things table
		self.cursor.execute("""CREATE TABLE things (
			item_name TEXT,
			display_name TEXT,
			category TEXT,
			price INTEGER,
			rarity TEXT,
			description TEXT,
			filepath TEXT,
			inventory_icon TEXT,
			from_mod TEXT
			)""")

		# Recipes table
		self.cursor.execute("""CREATE TABLE recipes (
			name TEXT,
			recipe_id INTEGER,
			count INTEGER,
			duration REAL,
			from_mod TEXT
			)""")

		# Learning table
		self.cursor.execute("""CREATE TABLE learn (
			from_object TEXT,
			recipe_name INTEGER,
			from_mod TEXT
			)""")

		######################
		## EXTENSION TABLES ##
		######################
		# Tables that contain more data about an object based on the type of object it is.
		# Consumables extension table
		self.cursor.execute("""CREATE TABLE consumables (
			item_name TEXT,
			rotting_multiplier REAL,
			max_stack INTEGER,
			food_value REAL,
			from_mod TEXT
			)""")

		# Objects extension table
		self.cursor.execute("""CREATE TABLE objects (
			item_name TEXT,
			colony_tags TEXT,
			race TEXT,
			printable INTEGER,
			from_mod TEXT
			)""")

		# Racial descriptions table. Yes, I could have merged this with other tables, but I won't.
		self.cursor.execute("""CREATE TABLE racial_descriptions (
			item_name TEXT,
			race TEXT,
			description TEXT,
			from_mod TEXT
			)""")

		# Objects that have the interact_action "OpenCraftingInterface"
		#self.cursor.execute("""CREATE TABLE crafting_objects (

		# The following three tables are essentially used as arrays in for the recipes table.. SQLite3 doesn't support arrays as a datatype.
		# Input table
		self.cursor.execute("""CREATE TABLE input (
			recipe_id INTEGER,
			item TEXT,
			count INTEGER,
			from_mod TEXT
			)""")

		# recipes_groups table
		self.cursor.execute("""CREATE TABLE recipes_groups (
			grouping TEXT,
			recipe_id INTEGER,
			from_mod TEXT
			)""")

		# station_groups table
		self.cursor.execute("""CREATE TABLE stations_groups (
			grouping TEXT,
			station TEXT,
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

	def json_get(self, key, data, error_on_fail=True, error_message="", default="?", error_level=logging.warning):
		"""
		Provides generic error handling when retrieving a key:value from a dictionary.
		:param key: (str) The key that you're trying to read.
		:param data: (dict) The dictionary you're trying to read from.
		:param error_on_fail: (bool) Whether it should log a message on fail, and raise an exception. Disabling this will turn off logging on error.
		:param error_message: (str) The message that should be printed if this operation fails.
		:param default: The value that will be returned if this value cannot be found.
		:param error_level: The level of error that should be logged.
			Setting to info or lower will prevent an exception from being raised.
			Changing default will prevent an exception from being raised.
		"""
		try:
			val = data[key]
		except KeyError:
			# Log error
			if error_on_fail:
				if error_message:
					err_msg = error_message
				else:
					err_msg = "File {} from mod {} has no key {}".format(self.filename, self.from_mod, key)
				error_level(err_msg)

				safe_errors = [logging.info, logging.debug]  # List of errors that will not raise an exception.
				if error_level not in safe_errors and default == "?":
					raise KeyError(err_msg + ". ".format(traceback.format_exc()))

			val = default

		# Add a "ValueError" exception.

		return val

# Exceptions
class Error(Exception):
	pass
class RecipeError(Error):
	"""Any error related to the reading of a recipe."""
	pass
class JsonGetError(Error):
	"""Returned if the json_get function is unable to read data."""
	pass



if __name__ == "__main__":
	program_folder = str(Path.cwd().parent)  # The location of this program's master folder.
	logging.basicConfig(filename='{}/log.txt'.format(program_folder), filemode="w", level=logging.DEBUG, format="[%(asctime)s] %(levelname)s: %(message)s", datefmt="%m/%d/%Y %I:%M:%S %p")
	d = Database("E:/Steam/steamapps")
	d.index_mods()


# woo line 1000 (right now).
