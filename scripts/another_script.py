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

d = db.Database("E:/Steam/steamapps")
d.remove_entries_of_mod("base")
#d.index_mods()
#d.remove_entries_of_mod("FrackinUniverse")
d.fill_db("E:\\Steam\\steamapps\\common\\Starbound\\test_unpack", "140db0a1158d7b2ddc0300513e8e5870")
#data = d.search("objects", column="description", where_value="(you)[^r]", regex=True)



# To mention in comment:

