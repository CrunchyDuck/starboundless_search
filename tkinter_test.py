import tkinter as tk
from PIL import ImageTK, Image # I will need to find a way to package pillow with my program.

root = tk.Tk()
root.title("Simple Calculator")

try:
	root.iconbitmap("icon.ico")
except tk._tkinter.TclError:
	pass # TODO: ERROR MESSAGE HERE


button_quit = tk.Button(root, text="EXIT", command=root.quit)



root.mainloop()


