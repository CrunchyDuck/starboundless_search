location_of_assets_pak = "E:/Steam/steamapps/workshop/content/211820/729480149/contents.pak"


import hashlib


def generate_checksum(file_path):
	hash_md5 = hashlib.md5()
	with open(file_path, "rb") as f:
		for chunk in iter(lambda: f.read(4096), b""):
			hash_md5.update(chunk)
	return hash_md5.hexdigest()



print(generate_checksum(location_of_assets_pak))
print("checksum'd")
input()


