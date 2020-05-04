import os
from pathlib import Path

location = Path("E:/Steam/steamapps/common/Starbound/test_unpack")

all_files = list(location.glob("**/*.*"))


extensions_set = set({})

for path in all_files:
	extension = str(path).split(".")[-1]
	extensions_set.add(extension)
extensions_set = list(extensions_set)
extensions_set.sort()

for i in extensions_set:
	print(i)
