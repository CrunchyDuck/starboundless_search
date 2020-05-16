try:
	import database as db
	import logging
	from pathlib import Path
except ModuleNotFoundError as e:
	print("{}\nThis likely means that there's a file missing. If so, please contact me (CrunchyDuck) and show me this error message.".format(e))
	input()
	exit()

program_folder = str(Path.cwd().parent) # The location of this program's master folder.
default_steamapps_directory = "C:/Program Files (x86)/Steam/steamapps" # This is where it will install to by default. If the user does not provide a directory, we will try this one, and yell if it is incorrect.


logging.basicConfig(filename='{}/log.txt'.format(program_folder), filemode="w", level=logging.DEBUG, format="[%(asctime)s] %(levelname)s: %(message)s", datefmt="%m/%d/%Y %I:%M:%S %p")



opening_text = """Welcome to the first version of Starboundless Search!
This is a program designed to make searching for anything in Starbound much easier.
Since this is the first version, the tools provided here are nowhere near reflective of the end product.
Case in point, the next step is ABSOLUTELY making a user interface, so you don't need to use a console :)
I won't ramble much more, if you wish to know more about this, have a suggestion, bug, etc, feel free to talk to me at https://discord.gg/TzTn4cy
======== Made with love by CrunchyDuck ========"""

textsearch = """Right now, this search engine has the base game indexed, and Frackin Universe.
You may search for any objects or recipes within either of those. More options and features available in the future."""

text_search_options = "\nEnter the number of the search type you wish to use:\n1. Recipe search\n2. Object search\n3. Credits"

text_search_recipe = """\nEnter the number of the field of the recipe you want to search for, and then the value to search for, E.G '2 iron':
1. Recipe name (Which is also what it creates, such as 'dumplin')
2. Recipe input (Such as 'iron b')" 
3. The bench the recipe is made at (Such as 'wooden work') (This might not work properly right now, sorry!)
4. What the recipe is learned from (Such as 'tung')"""

text_search_object = """\nEnter the number of the field of the object you wish to search for and then the value to search for, E.G '1 concrete':
1. Object name (Such as concrete)
2. Item ID (Such as concreteblock)
3. Part of the item's description (Such as 'strange, unidentifiable liquid')
4. Category the object is in (Such as Crafting)"""

credits = """\nCode and concept created by CrunchyDuck in Python 3.8
==== BEAUTIFUL PEOPLE ====
A huge thank you to my partner, who has supported me during this entire project.
Thank you to Shinigami Apples#7335 from the Frackin Universe Discord for helping me investigate output recipes.
Thank you to Pixelflame5826#1645 from the main Starbound discord for investigating how long crafting recipes take by default.
Thank you to all of the Frackin Universe Discord for just being nice and giving me the motivation to keep working.
<3"""

unrecognized_input = "Value {} is not recognized. Nice try."

d = db.Database("E:/Steam/steamapps")
#d.clear_database()
#d.index_mods()
#d.unpack("E:/Steam/steamapps/common/Starbound/assets/packed.pak", "140db0a1158d7b2ddc0300513e8e5870")

print(opening_text)
print(textsearch)
# This was thrown together in a couple hours and doesn't represent how the engine will function when I have the UI running.
while True:
	option = ""
	search_val = ""

	# object vals
	obj_name = ""
	itemID = ""
	description = ""
	category = ""

	# recipe vals
	creates = ""
	inputval = ""
	bench = ""
	learned_from = ""
	duration = 0
	from_mod = ""

	# Check which menu the user wishes to enter.
	while True:
		print(text_search_options)
		option = input()
		op_choices = ["1", "2", "3"]
		if option in op_choices:
			break
		else:
			print(unrecognized_input.format(option))

	# Search recipe
	if option == "1":
		# Get which field the user wishes to search
		while True:
			print(text_search_recipe)
			option = input()
			num = option[0]
			if num == "1" or num == "2" or num == "3" or num == "4":
				break
			else:
				print(unrecognized_input.format(num))

		# Search in the appropriate field
		search_val = option[2:]
		print(num)
		if num == "1":
			creates = search_val
		elif num == "2":
			inputval = search_val
		elif num == "3":
			bench = search_val
		elif num == "4":
			learned_from = search_val

		print("Searching for creates={}, input={}, duration={}, bench={}, from_mod={}...\n".format(creates, inputval, duration, bench, from_mod))
		recipeIDs = d.search_recipe(creates, inputval, duration, bench, from_mod)
		if recipeIDs != "?":
			recipe_data = d.get_recipe_information(recipeIDs)
		else:
			recipe_data = "No Recipes"

		# This takes the above parsed data and displays it for the user.
		if recipe_data != "No Recipes":
			for recipe in recipe_data:
				recipe_id = recipe[0][0]
				duration = recipe[0][1]
				from_mod = recipe[0][2]

				learned_from = ""
				list_size = len(recipe[1])
				for index, learned in enumerate(recipe[1]):
					if index == 0:
						learned_from = learned
					elif index == (list_size - 1):  # Last entry of the list
						learned_from += " and {}".format(learned)
					else:
						learned_from += ", {}".format(learned)

				output = ""
				recipe_name = ""
				num_of_outputs = int(len(recipe[2]) / 2)  # This is divided by two because there will always be 2 entries per output.
				for index in range(num_of_outputs):
					list_pos = index * 2
					object_name = d.remove_colour_tags(d.convert_id(id=recipe[2][list_pos]))
					object_count = recipe[2][list_pos + 1]

					if index == 0:
						recipe_name = "{}".format(object_name)
						output = "{} (x{})".format(object_name, object_count)
					else:
						output += ", {} (x{})".format(object_name, object_count)
						recipe_name += "{}".format(object_name)  # Hopefully this never happens.

				inputval = ""
				num_of_inputs = int(len(recipe[3]) / 2)  # This is divided by two because there will always be 2 entries per input.
				for index in range(num_of_inputs):
					list_pos = index * 2
					object_name = d.remove_colour_tags(d.convert_id(id=recipe[3][list_pos]))
					object_count = recipe[3][list_pos + 1]

					if index == 0:
						inputval = "{} (x{})".format(object_name, object_count)
					else:
						inputval += ", {} (x{})".format(object_name, object_count)

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
				Item ID: {}
				From Mod: {}
				""".format(recipe_name, benches, inputval, output, learned_from, duration, groups, itemID, from_mod)
				print(print_value)
		else:
			print("Could not find any recipes with the following variables: creates={}, input={}, duration={}, bench={}, from_mod={}\n".format(creates, inputval, duration, bench, from_mod))


	# search object
	elif option == "2":
		# Get which field the user wishes to search
		while True:
			print(text_search_object)
			option = input()
			num = option[0]
			if num == "1" or num == "2" or num == "3" or num == "4":
				break
			else:
				print(unrecognized_input.format(num))

		# Search in the appropriate field
		search_val = option[2:]
		if num == "1":
			obj_name = search_val
		elif num == "2":
			itemID = search_val
		elif num == "3":
			description = search_val
		elif num == "4":
			category = search_val

		print("Searching for object name={}, itemID={}, description={}, category={}, from_mod={}...\n".format(obj_name, itemID, description, category, from_mod))
		objectIDs = d.search_object(obj_name, itemID, description, category, from_mod)


	# Credits <3
	elif option == "3":
		print(credits)



#d.remove_entries_of_mod("base")
#d.remove_entries_of_mod("FrackinUniverse")
#d.fill_db("E:\\Steam\\steamapps\\common\\Starbound\\test_unpack", "140db0a1158d7b2ddc0300513e8e5870")
#d.fill_db("C:\\Users\\Adam\\Desktop\\starbound_mod\\starboundless_search\\FU\\729480149", "06b43f04852a13acb54819fb6b94b427")
#data = d.search("recipes", column="input", where_value="rainbow", regex=True)
#data = d.search_recipe("recipes_groups", where_value=["grouping='plain'"])
#d.update()
search = ""

# SEARCH FUNCTION (seems to be functional)
if search == "re":
	creates = "star-killer"
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

	# This takes the above parsed data and displays it for the user.
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
elif search == "ob":
	name = "assemblyline"
	d.cursor.execute("SELECT * FROM objects WHERE display_name REGEXP '{}'".format(name))
	d.cursor.execute("SELECT * FROM stations_groups WHERE station REGEXP '{}'".format(name))
	for a in d.cursor.fetchall():
		print(a)

