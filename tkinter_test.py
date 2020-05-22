import tkinter as tk
from PIL import ImageTk, Image

def ui_back(image_number):
	new_image_i = image_number - 1
	arrow_button(new_image_i)

def ui_forward(image_number):
	new_image_i = image_number + 1
	arrow_button(new_image_i)

def arrow_button(new_image_i):
	global my_label
	global button_forward
	global button_back
	global my_img

	num_of_images = len(my_img) - 1

	my_label.grid_forget()
	my_label = tk.Label(image=my_img[new_image_i])
	my_label.grid(row=0, column=0, columnspan=3)

	if new_image_i != 0:
		button_back = tk.Button(root, text="<<", command=lambda: ui_back(new_image_i))
	else:
		button_back = tk.Button(root, text="<<", state=tk.DISABLED)
	if new_image_i != num_of_images:
		button_forward = tk.Button(root, text=">>", command=lambda: ui_forward(new_image_i))
	else:
		button_forward = tk.Button(root, text=">>", state=tk.DISABLED)

	button_back.grid(row=1, column=0)
	button_forward.grid(row=1, column=2)




img_folder = "C:/Users/Adam/Desktop/starbound_mod/starboundless_search/images"

root = tk.Tk()
root.title("Simple Calculator")
root.iconbitmap("{}/icon.ico".format(img_folder))

my_img = []
my_img.append(ImageTk.PhotoImage(Image.open("{}/notepad.png".format(img_folder))))
my_img.append(ImageTk.PhotoImage(Image.open("{}/AERODYNAMIC COW 2.png".format(img_folder))))
my_img.append(ImageTk.PhotoImage(Image.open("{}/duno.png".format(img_folder))))
my_img.append(ImageTk.PhotoImage(Image.open("{}/icon.ico".format(img_folder))))



my_label = tk.Label(image=my_img[0])
my_label.grid(row=0, column=0, columnspan=3)


button_back = tk.Button(root, text="<<", state=tk.DISABLED)
button_quit = tk.Button(root, text="EXIT", command=root.quit)
button_forward = tk.Button(root, text=">>", command=lambda: ui_forward(0))

button_back.grid(row=1, column=0)
button_quit.grid(row=1, column=1)
button_forward.grid(row=1, column=2)

root.mainloop()


