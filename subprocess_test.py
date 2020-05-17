import subprocess
import pathlib
from os import makedirs

steamapps_path = "E:/Steam/steamapps" # Path of steamapps



master_path = pathlib.Path(steamapps_path)
starbound_path = pathlib.Path(str(master_path) + "/common/Starbound")
unpack_exe_path = pathlib.Path(str(starbound_path) + "/win32/asset_unpacker.exe")

asset_packed_path = pathlib.Path(str(starbound_path) + "/assets/packed.pak")
asset_unpacked_path = str(starbound_path) + "/test_unpack"
makedirs(str(asset_unpacked_path))

unpack_command = "{0} \"{1}\" \"{2}\"".format(str(unpack_exe_path), str(asset_packed_path), str(asset_unpacked_path))
print(unpack_command)

#res = subprocess.run(unpack_command)

print(res)
