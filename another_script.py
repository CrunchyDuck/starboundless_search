try:
	import database as db
	import logging
	from pathlib import Path
	import traceback
	from os import getcwd
except ModuleNotFoundError as e:
	print("{}\nThis likely means that there's a file missing. If so, please contact me (CrunchyDuck) and show me this error message.".format(e))
	input()
	exit()


def mainloop():
	valid_choices = ["1", "2", "3"]  # What the user is allowed to input.
	# Check which menu the user wishes to enter.
	while True:
		print(text_search_options)
		option = input("Input: ")
		print()
		if option in valid_choices:
			break
		else:
			print(unrecognized_input.format(option))

	# Search recipe
	if option == "1":
		recipeloop()


	# search object
	# DISABLED RN :D
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


	# Info...
	elif option == "3":
		infoloop()

def recipeloop():
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

	valid_choices = ["1", "2", "3", "4", "5"]
	# Get which field the user wishes to search
	while True:
		print(text_search_recipe)
		option = input()
		print()
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
	elif num == "5":
		return
	print()

	# Perform a search
	searching_for = "Searching for \"{}\"".format(search_field)
	print("Searching...")
	recipeIDs = d.search_recipe(creates, inputval, duration, bench, from_mod, display_name_search=False)
	all_recipe_data = d.return_recipes_data(recipeIDs)

	# Print all results to a file.
	if all_recipe_data:
		filename = search_field  # No it can't be undefined shut up.
		file_path = "{}/{}.txt".format(Path.cwd(), filename)
		with open(file_path, "w") as f:
			f.write("{}\n==========================================\n".format(searching_for))
			for recipe in all_recipe_data:
				f.write(recipe)
		print("Printed results to file located at {}".format(file_path))
	else:
		print("Could not find any recipes with the following variables: creates={}, input={}, duration={}, bench={}, from_mod={}\n".format(creates, inputval, duration, bench, from_mod))
	recipeloop()

def infoloop():
	valid_choices = ["1", "2", "3", "4"]  # What the user is allowed to input
	while True:
		print(info)
		option = input("Input: ")
		print()
		if option in valid_choices:
			pass
		else:
			print(unrecognized_input.format(option))
			continue

		if option == "1":
			print(about_fu)
		elif option == "2":
			print(about_sls)
		elif option == "3":
			print(credits)
		elif option == "4":
			return

# Setup
try:
	program_folder = str(Path.cwd()) # The location of this program's master folder.
	default_steamapps_directory = "C:/Program Files (x86)/Steam/steamapps" # This is where it will install to by default. If the user does not provide a directory, we will try this one, and yell if it is incorrect.
	logging.basicConfig(filename='{}/log.txt'.format(program_folder), filemode="w", level=logging.DEBUG, format="[%(asctime)s] %(levelname)s: %(message)s", datefmt="%m/%d/%Y %I:%M:%S %p")

	# Console text
	opening_text = """Welcome to the first (second) version of Starboundless Search!
This is a program designed to make searching for anything in Starbound much easier.
Since this is the first version, the tools provided here are nowhere near reflective of the end product.
Case in point, the next step is ABSOLUTELY making a user interface, so you don't need to use a console :)
I won't ramble much more, if you wish to know more about this, have a suggestion, bug, etc, feel free to talk to me at https://discord.gg/TzTn4cy
======== Made with love by CrunchyDuck ========"""
	textsearch = """Right now, this search engine has the base game indexed, and Frackin Universe.
You may search for any things or recipes within either of those.
More options and features available in the future.\n"""
	text_search_options = "Enter the number of the search type you wish to use:\n1. Recipe search\n2. Object search (whoops I couldn't get this running before release date)\n3. Info"
	text_search_recipe = """\nEnter the number of the field of the recipe you want to search for:
1. Recipe name (Which is also what it creates, such as 'dumplin')
2. Recipe input (Such as 'iron b')" 
3. The bench the recipe is made at (Such as 'wooden work') (This might not work properly right now, sorry!)
4. What the recipe is learned from (Such as 'tung')
5. Back"""
	text_search_object = """\nEnter the number of the field of the object you wish to search for:
1. Object name (Such as concrete)
2. Item ID (Such as concreteblock)
3. Part of the item's description (Such as 'strange, unidentifiable liquid')
4. Category the object is in (Such as Crafting)"""

	info = "Choose which rant to hear:\n1. About Frackin Universe...\n2. About Starboundless Search (And the future)...\n3. Credits <3\n4. Supporting\n5. Back"
	about_fu = "Frackin Universe is not nice to me. The code I created to index everything\n" \
			   "works just fine on the basic game, and on most other mods I've tested it on.\n" \
			   "However, FU has a lot of unique ways of doing things. This makes working with\n" \
			   "it an absolute nightmare, at least programmatically.\n" \
			   "Some functions (for now) will flat out not work in regards to FU due to this.\n" \
			   "I will absolutely be working on this in the future. But right now, I've received\n" \
			   "little help in regards to tackling this, so I have omitted it for my sanity.\n" \
			   "Note though, nearly everything in the normal game files is fine and dandy.\n"
	about_sls = "Starboundless Search (Shortened to SLS) is designed to make searching for\n" \
				"ANYTHING in Starbound far, far easier. Instead of relying on poorly maintained\n" \
				"wikis and worse in game tools, you should be able to search nigh any data you\n" \
				"have.\n" \
				"The current state of SLS is of course not the final product. Major things:\n" \
				"USER. INTERFACE. That's the next stop.\n" \
				"Object searching! Finding objects and their data is important.\n" \
				"More ways to obtain things! Input/output benches, monster drops, biome spawns\n" \
				"and loot tables to name just a few.\n" \
				"\nIf you want to talk to me directly, see more stuff, suggest additions or changes,\n" \
				"anything, feel free to join me on Discord:\n" \
				"https://discord.gg/TzTn4cy\n"
	about_supporting = "If you like my attempt at making tools and cool things like this and want to support\n" \
					   "me further, above all telling me that you like this and joining my dumb Discord is the\n" \
					   "best way by far, found here:\n" \
					   "https://discord.gg/TzTn4cy\n" \
					   "I live only for the approval of others~\n" \
					   "Though if you want to make me question if what I'm doing is moral, you can donate to me too!\n" \
					   "https://ko-fi.com/crunchyduck\nThank you for your time.\n"
	credits = "==== BEAUTIFUL PEOPLE ====\n" \
			  "Everything you see here made by CrunchyDuck. I need to sleep.\n" \
			  "A huge thank you to my partner, who has supported me during this entire project.\n" \
			  "Thank you to Shinigami Apples#7335 from the Frackin Universe Discord for helping\n" \
			  "me investigate output recipes.\n" \
			  "Thank you to Pixelflame5826#1645 from the main Starbound discord for investigating\n" \
			  "how long crafting recipes take by default.\n" \
			  "Thank you anyone who has shown an interest in my project, for giving me the\n" \
			  "motivation to keep working on this.\n" \
			  "<3\n"
	unrecognized_input = "Value {} is not recognized. Nice try."

	d = db.Database("E:/Steam/steamapps")
	#d.clear_database()
	#d.index_mods()
	#d.unpack("E:/Steam/steamapps/common/Starbound/assets/packed.pak", "140db0a1158d7b2ddc0300513e8e5870")

	print(opening_text)
	print(textsearch)
except Exception as e:
	print("Wow, an error, even in such a simple program. Too bad!\nBut really, you should send me the following:\n\n{}".format(traceback.format_exc()))
	input()
	exit()

# Console app run
try:
	while True:
		mainloop()
except Exception:
	print("Wow, an error, even in such a simple program. Too bad!\nBut really, you should send me the following:\n\n{}".format(traceback.format_exc()))
	input("Press enter to continue...")

#print(d.read_object_file("E:/Steam/steamapps/common/Starbound/test_unpack/objects/crafting/ironanvil/ironanvil.object"))
#print(d.cursor.execute("SELECT * FROM things WHERE item_name='fishdumplings'").fetchall())
#print(d.read_consumable_file("E:/Steam/steamapps/common/Starbound/test_unpack/items/generic/food/tier1/meatdumplings.consumable"))
#print(d.cursor.execute("SELECT * FROM recipes_groups WHERE recipe_id=528").fetchall())

#d.clear_database()
#d.fill_db(getcwd() + "\\unpack\\140db0a1158d7b2ddc0300513e8e5870", "140db0a1158d7b2ddc0300513e8e5870")
#d.fill_db(getcwd() + "\\FU\\729480149", "06b43f04852a13acb54819fb6b94b427")

# ALL crafting groups that are not assigned to a crafting table/object. Some of these (such as 'all' are fine.)
#myset = set()
#v = d.cursor.execute("SELECT grouping FROM recipes_groups WHERE grouping NOT IN (SELECT grouping FROM stations_groups)").fetchall()
#for r in v:
#	myset.add(r)
#print(myset)
