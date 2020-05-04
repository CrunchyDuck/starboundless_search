from pathlib import Path # Allows me to fetch a list of all files within an area easily.
from subprocess import run # Used to unpack the .pak files.
from os import mkdir as makedir
from shutil import rmtree

def Database(steamapps_directory):
	object = database()
	object.steam_dir = steamapps_directory
	object.mods_dir = Path(object.steam_dir + "/workshop/content/211820")  # Folder for steam mods.
	object.starbound_dir = Path(str(object.steam_dir) + "/common/Starbound")  # Starbound folder
	object.starbound_mods_dir = Path(str(object.starbound_dir) + "/mods")  # Location of the mods folder in the starbound folder
	return object



class database():

	def __init__(self):
		self.program_folder = str(Path.cwd().parent) # The location of this program's master folder.

		self.steam_dir = "" # This will be used to search for starbound's files.
		self.mods_dir = ""  # Folder for steam mods.
		self.starbound_dir = ""  # Starbound folder
		self.starbound_mods_dir = ""  # Location of the mods folder in the starbound folder

	def index_mods(self):
		# How do I deal with a mod that has been removed? We'll likely need to index all mods again as there's no way to identify what comes from where.
		# Search for all mods in the user's files (steam mods and on disk mods)
		starbound_mod_files = list(self.starbound_mods_dir.glob("*.pak"))  # All mods within the starbound mod directory.
		steam_mod_files = list(self.mods_dir.glob("**/*.pak"))  # Get all .pak stored within the steam mod directory

		mod_files = [] # The directories of each mod the user has.
		mod_names = [] # All of the file names of the mods. We'll index these in the "indexed mods" after we're done. This should closely mirror mod_files
		with open(self.program_folder + "/data/modlist.fox") as f: indexed_mods = f.read() # A list of all mods that we have already indexed.

		for mod in starbound_mod_files:
			mod_id = mod.stem
			found = indexed_mods.find(mod_id)
			if found == -1:
				mod_files.append(str(mod))
				mod_names.append(mod_id)

		for mod in steam_mod_files:
			mod_id = self.get_path_name((str(mod.parent))) # The ID of this mod. Will be used to identify the mod to check if we've already indexed it.
			mod_id = mod_id[1:] # The first character will be a /, this removes that.
			found = indexed_mods.find(mod_id)
			if found == -1:
				mod_files.append(str(mod))
				mod_names.append(mod_id)


		# Unpack the new mods we've found so we can parse the JSON data.
		unpack_exe = str(self.starbound_dir) + "/win32/asset_unpacker.exe" # The location of teh asset unpacker. This converts .pak files into their source code.
		unpack_location = "{}/unpack".format(self.program_folder) # The unpack directory in this program.

		if not Path(unpack_exe).exists: # Make sure the unpack exe is actually there. If the user has deleted it, scream loudly.
			print("""Could not find asset_unpacker.exe in the starbound files.
			You haven't deleted it, have you? If you have, why on earth-.
			It should be located at {}""".format(unpack_exe)) # TODO hook this into the error/log reporting system
			exit() # Close the program because it cannot possibly run.

		if Path(unpack_location).exists():
			rmtree(unpack_location) # This will remove any files from the last unpacks that might not have gotten cleaned up.
		makedir(unpack_location)


		for index, mod in enumerate(mod_files):
			break
			print("Unpacking {}...".format(mod))

			mod_unpack_location = "{}/{}".format(unpack_location, mod_names[index])  # The place we'll unpack mods temporarily to parse through. Each mod will have its own folder within this.
			makedir(mod_unpack_location)
			asset_packed_path = mod
			unpack_command = "{} \"{}\" \"{}\"".format(unpack_exe, asset_packed_path, mod_unpack_location)

			run(unpack_command) # Unpack the files. There's almost certainly going to be errors with this that I cannot fathom, so I'll need to rely on community testing.
			with open(self.program_folder + "/data/modlist.fox", "a") as f: indexed_mods.write(mod_names[index] + "\n")
			# TODO: Get name of object from metadata here.

			print("Finished unpacking {}".format(mod))
			break

		# Update the database with the unpacked mods
		def update_database(unpacked_mods_dir):  # With the newly unpacked mods, we need to go over all the files and pick out the important data.
			def get_recipes():
				return directory_of_recipes

			def get_objects():
				# File extensions that contain data we'll need:
				# .liqitem, .object .matitem, .chest, .legs, .head, .activeitem, .augment, .back, .beamaxe, .consumable, .currency, .flashlight, .harvestingtool, .inspectiontool, .instrument, .item, .miningtool,, .objectdisabled, .painttool,
				# .thrownitem, .tillingtool, .wiretool
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


	# Private functions. Things that will only be used within this class.
	def get_path_name(self, directory):
		dir_len = len(directory)
		filename = ""

		for i in range(dir_len):
			if directory[-i] == "\\":
				for j in range(i):
					filename = filename + directory[-i + j]
				break
		return filename



d = Database("E:/Steam/steamapps")
d.index_mods()
