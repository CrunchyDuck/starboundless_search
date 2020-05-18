try:
	import database as db
	import logging
	from pathlib import Path
	import traceback
except ModuleNotFoundError as e:
	print("{}\nThis likely means that there's a file missing. If so, please contact me (CrunchyDuck) and show me this error message.".format(e))
	input()
	exit()
try:
	program_folder = str(Path.cwd()) # The location of this program's master folder.
	default_steamapps_directory = "C:/Program Files (x86)/Steam/steamapps" # This is where it will install to by default. If the user does not provide a directory, we will try this one, and yell if it is incorrect.


	logging.basicConfig(filename='{}/log.txt'.format(program_folder), filemode="w", level=logging.DEBUG, format="[%(asctime)s] %(levelname)s: %(message)s", datefmt="%m/%d/%Y %I:%M:%S %p")


	# Console text
	opening_text = """Welcome to the first version of Starboundless Search!
This is a program designed to make searching for anything in Starbound much easier.
Since this is the first version, the tools provided here are nowhere near reflective of the end product.
Case in point, the next step is ABSOLUTELY making a user interface, so you don't need to use a console :)
I won't ramble much more, if you wish to know more about this, have a suggestion, bug, etc, feel free to talk to me at https://discord.gg/TzTn4cy
======== Made with love by CrunchyDuck ========"""
	textsearch = """Right now, this search engine has the base game indexed, and Frackin Universe.
You may search for any things or recipes within either of those. More options and features available in the future."""
	text_search_options = "\nEnter the number of the search type you wish to use:\n1. Recipe search\n2. Object search (whoops I couldn't get this running before release date)\n3. Credits"
	text_search_recipe = """\nEnter the number of the field of the recipe you want to search for:
1. Recipe name (Which is also what it creates, such as 'dumplin')
2. Recipe input (Such as 'iron b')" 
3. The bench the recipe is made at (Such as 'wooden work') (This might not work properly right now, sorry!)
4. What the recipe is learned from (Such as 'tung')"""
	text_search_object = """\nEnter the number of the field of the object you wish to search for:
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

		valid_choices = ["1", "2", "3"] # What the user is allowed to input.
		# Check which menu the user wishes to enter.
		while True:
			print(text_search_options)
			option = input()
			if option in valid_choices:
				break
			else:
				print(unrecognized_input.format(option))

		# Search recipe
		if option == "1":
			valid_choices = ["1", "2", "3", "4"]
			# Get which field the user wishes to search
			while True:
				print(text_search_recipe)
				option = input()
				num = option
				if num in valid_choices:
					break
				else:
					print(unrecognized_input.format(num))

			# Search in the appropriate field
			if num == "1":
				search_field = input("Enter recipe name/output: ")
				creates = search_field
			elif num == "2":
				search_field = input("Enter recipe input: ")
				inputval = search_field
			elif num == "3":
				search_field = input("Enter workstation for this recipe: ")
				bench = search_field
			elif num == "4":
				search_field = input("Enter which item this recipe is learned from: ")
				learned_from = search_field

			# Perform a search
			print("Searching for creates={}, input={}, duration={}, bench={}, from_mod={}...".format(creates, inputval, duration, bench, from_mod))
			recipeIDs = d.search_recipe(creates, inputval, duration, bench, from_mod, display_name_search=False)
			all_recipe_data = d.return_recipes_data(recipeIDs)

			# Print all results to a file.
			if all_recipe_data:
				filename = search_field
				file_path = "{}/{}.txt".format(Path.cwd(), filename)
				with open(file_path, "w") as f:
					for recipe in all_recipe_data:
						f.write(recipe)
				print("Printed results to file located at {}".format(file_path))
			else:
				print("Could not find any recipes with the following variables: creates={}, input={}, duration={}, bench={}, from_mod={}\n".format(creates, inputval, duration, bench, from_mod))


		# search object
		# DISABLE RN :D
		elif option == "2000":
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
except Exception as e:
	print("Wow, an error, even in such a simple program. Too bad!\nBut really, you should send me the following:\n\n{}".format(traceback.format_exc()))
	input()
	exit()




#d.clear_database()
#d.fill_db("E:\\Steam\\steamapps\\common\\Starbound\\test_unpack", "140db0a1158d7b2ddc0300513e8e5870")
#d.fill_db("C:\\Users\\Adam\\Desktop\\starbound_mod\\starboundless_search\\FU\\729480149", "06b43f04852a13acb54819fb6b94b427")


