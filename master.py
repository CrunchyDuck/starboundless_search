import os
from enum import Enum

# The main document that will handle... Everything.
# I will try to mark out a list of functions I need and stuff I must consider.


# This code should be used to unpack all of the .pak data from the mods, and index all recipes and items stored within.
# subprocess_test.py is essentially how I'll want to do this, and I could combine it with the code used to search for mods in starbound_backup.py
def index_mods():
	def find_mods(): # Search for all mods in the user's files
		use_part_of_starbound_backup.py()
		return array_of_mod_directories

	def check_if_mod_is_known(mods): # Check if this mod has already been indexed. I think I will have to do this after I unpack the mods as there seems to
		return array_of_mod_directories

	def unpack_mods(mods_to_unpack_array): # Unpack the mods to the directory of this python file so we can access the data stored within.
		subprocess_text.py()
		return directory_of_unpack

	def update_database(unpacked_mods_dir): # With the newly unpacked mods, we need to go over all the files and pick out the important data.
		def get_recipes():
			return directory_of_recipes

		def get_objects():
			# File extensions that contain data we'll need:
			# .liquid, .liqitem, .object .matitem
			return directory_of_objects


		def update_objects():
			def update_learnDB(): # This database will contain any recipe that is learned from picking up an object, and what you learn from it.
				return nothing

			return nothing

		def update_recipes():
			def update_inputDB(): # The input db needs to be separate from the update db because it is often an array
				return nothing

			def update_outputDB(): # It's possible I'll need to do the same as the input DB, as it is *possible* albeit uncommon for a mod to have multiple outputs.
				return nothing

			return nothing



def search_object_id_for_real_name(object_id): # SEarch the database for the correct "name" of an object. E.G Concrete Block has the itemID of concretematerial. We need to convert concretematerial to Concrete Block.
	return object_name


def standard_search(text, search_type, search_part=False):

	if search_part: # This should be an option the user can toggle on. When this is one, the search engine will return all values that contain this piece or more. It will never return a single item.
		pass
	else: # If search path is off, then we'll check the SQL database for a perfect match. If this isn't found, then we'll treat it as if it was "search part"
		if search_type == "object": # The search type will determine if they're searching for recipes or for objects.
			pass
		elif search_type == "recipe": # If recipe, it'll return all of the recipes this object is used in the making of.
			pass


# This should be made to handle any errors.
class ErrorManager():
	def __init__(self):
		self.err_path = os.getcwd()
		self.file_name = "log.txt"
		# Maybe I could have a "last error" variable?
		with open(self.file_name, "w") as f: # Overwrite an existing file, or create one.
			pass

	def err(self, message, err_level = 1):
		# Update error file
		with open(self.file_name, "a") as file:
			file.write("{}: {}".format(ErrorEnum(err_level).name, message))

		# Print error to console
		if err_level <= 1:
			print("{} error: {}\n".format(ErrorEnum(err_level).name, message))


# Will be used to classify the severity of the error.
class ErrorEnum(Enum):
	Critical = 0
	Major = 1
	Minor = 2
	Notice = 3
	Information = 4

