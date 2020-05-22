# Creates the folder that'll be distributed to users.
from subprocess import run
import os
import shutil

# CREATE .EXE
# This probably won't work on non-windows PCs. Try it if you want, but you should probably use a console to create the file otherwise.
dir = os.getcwd()
command = "pyinstaller --console --onefile"
setup_file = dir + "/another_script.py"
file_name = "--name Starboundless_Search"
add_data = " --add-data {0}/data/database.foxdb;data --add-data {0}/data/r_id.fox;data".format(dir)

run("{} {} {}".format(command, setup_file, file_name))

# ADD DATA
dist_file = dir + "/dist"
dist_data = dist_file + "/data"
data_file = dir + "/data"
img_file = dir + "/images"
try:
	os.mkdir(dist_data)
except FileExistsError:
	pass

# Copy from datafile
data_files_to_include = ["/database.foxdb", "/r_id.fox"]
for filename in data_files_to_include:
	shutil.copy(data_file + filename, dist_data)

# Add misc data
shutil.copy(dir + "/credits_how_its_made.txt", dist_file)
shutil.copy(dir + "/LICENCE", dist_file)
