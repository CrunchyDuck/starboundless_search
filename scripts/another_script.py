try:
	import database as db
	import logging
	from pathlib import Path
	import re
except ModuleNotFoundError as e:
	print("{}\nThis likely means that there's a file missing. If so, please contact me (CrunchyDuck) and show me this error message.".format(e))
	input()
	exit()

program_folder = str(Path.cwd().parent) # The location of this program's master folder.
default_steamapps_directory = "C:/Program Files (x86)/Steam/steamapps" # This is where it will install to by default. If the user does not provide a directory, we will try this one, and yell if it is incorrect.


logging.basicConfig(filename='{}/log.txt'.format(program_folder), filemode="w", level=logging.DEBUG, format="[%(asctime)s] %(levelname)s: %(message)s", datefmt="%m/%d/%Y %I:%M:%S %p")






d = db.Database("E:/Steam/steamapps")
#d.remove_entries_of_mod("base")
#d.index_mods()
#d.remove_entries_of_mod("FrackinUniverse")
#d.fill_db("E:\\Steam\\steamapps\\common\\Starbound\\test_unpack", "140db0a1158d7b2ddc0300513e8e5870")
#data = d.search("recipes", column="input", where_value="rainbow", regex=True)
#data = d.search_recipe("recipes_groups", where_value=["grouping='plain'"])


creates = "meat"
input = ""
duration = 0
bench = ""
from_mod = ""
print("Searching for creates={}, input={}, duration={}, bench={}, from_mod={}...\n".format(creates, input, duration, bench, from_mod))
recipeIDs = d.search_recipe(creates, input, duration, bench, from_mod)
if recipeIDs != "?":
	recipe_data = d.get_recipe_information(recipeIDs)
else:
	recipe_data = "No Recipes"

if recipe_data != "No Recipes":
	for recipe in recipe_data:
		duration = recipe[0][1]

		learned_from = ""
		list_size = len(recipe[1])
		for index, learned in enumerate(recipe[1]):
			if index == 0:
				learned_from = learned
			elif index == (list_size - 1): # Last entry of the list
				learned_from += " and {}".format(learned)
			else:
				learned_from += ", {}".format(learned)

		output = ""
		recipe_name = ""
		num_of_outputs = int(len(recipe[2]) / 2) # This is divided by two because there will always be 2 entries per output.
		for index in range(num_of_outputs):
			list_pos = index * 2
			object_name = d.remove_colour_tags(d.convert_id(id=recipe[2][list_pos]))
			object_count = recipe[2][list_pos + 1]

			if index == 0:
				recipe_name = "{}".format(object_name)
				output = "{} (x{})".format(object_name, object_count)
			else:
				output += ", {} (x{})".format(object_name, object_count)
				recipe_name += "{}".format(object_name) # Hopefully this never happens.


		input = ""
		num_of_inputs = int(len(recipe[3]) / 2)  # This is divided by two because there will always be 2 entries per input.
		for index in range(num_of_inputs):
			list_pos = index * 2
			object_name = d.remove_colour_tags(d.convert_id(id=recipe[3][list_pos]))
			object_count = recipe[3][list_pos + 1]

			if index == 0:
				input = "{} (x{})".format(object_name, object_count)
			else:
				input += ", {} (x{})".format(object_name, object_count)

		benches = ""
		list_size = len(recipe[4])
		for index, bench_name in enumerate(recipe[4]):
			bench_name_clean = d.remove_colour_tags(bench_name)
			if index == 0:
				benches = "{}".format(bench_name_clean)
			elif index == (list_size - 1):
				benches += " and {}".format(bench_name_clean)
			else:
				benches += ", {}".format(bench_name_clean)

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
		""".format(recipe_name, benches, input, output, learned_from, duration, groups)
		print(print_value)
else:
	print("Could not find any recipes with the following variables: creates={}, input={}, duration={}, bench={}, from_mod={}\n".format(creates, input, duration, bench, from_mod))