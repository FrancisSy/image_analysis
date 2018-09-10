#!/usr/bin/python3
# works properly on Python version 3.6
# currently only supports jpeg files

import os
import numpy as np
from time import time
from math import sqrt
from queue import Queue
from tkinter import *
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageChops # Pillow Image fork
from skimage.feature import match_template

# global constants for image analysis
max_length = 640 # height
max_width = 640
RMS = 50 # root mean square

class imageAnalysis():
    def __init__(self, master): # class constructor
        # master window
        self.master = master
        self.master.title('Image Analysis')
        self.master.resizable(False, False)
        self.main_frame = ttk.Frame(self.master)
        self.main_frame.pack(padx = 5, pady = 5)
        ttk.Label(self.main_frame, text = 'Search Directory:').grid(row = 0, column = 0, sticky = 'w')

        # directory window
        self.path_entry = ttk.Entry(self.main_frame, width = 54)
        self.path_entry.grid(row = 1, column = 0, sticky ='e')
        self.path_entry.insert(0, '.\\default') # default search folder

        # browse button
        self.browse_button = ttk.Button(self.main_frame, text = 'Browse...', command = self.browse)
        self.browse_button.grid(row = 1, column = 1, sticky = 'w')
        self.search_button = ttk.Button(self.main_frame, text='Find Subset Images', command=self.search)
        self.search_button.grid(row=2, column=0, columnspan=2)

        # result table
        self.results_table = ttk.Treeview(self.main_frame, column=('subset'))
        self.results_table.heading('#0', text='Original Image')
        self.results_table.column('#0', width=200)
        self.results_table.heading('subset', text='Subset Image')
        self.results_table.column('subset', width=200)

        # status frame
        self.status_frame = ttk.Frame(self.master)
        self.status_frame.pack(fill=BOTH, expand=True)
        self.status_var = StringVar()
        self.status_label = ttk.Label(self.status_frame, textvariable=self.status_var)

        # progress bar
        self.progress_var = DoubleVar()
        self.progressbar = ttk.Progressbar(self.status_frame, mode='determinate',
                                           variable=self.progress_var)

    def browse(self):
        path = filedialog.askdirectory(initialdir = self.path_entry.get())
        self.path_entry.delete(0, END)
        self.path_entry.insert(0, path)

    def search(self):
        self.start_time = time()

        # file extensions supported
        extension = ['.JPG', '.jpg']

        # build a jpeg list in the directory
        try:
            self.path = self.path_entry.get()
            images = list(entry for entry in os.listdir(self.path) if entry.endswith(tuple(extension)))
        except:
            messagebox.showerror(title = 'Error: Invalid Directory',
                                 message = 'Invalid Search Directory:\n' + self.path)
            return

        if len(images) < 2:
            messagebox.showerror(title='Error: Not Enough Images',
                                 message='Program needs at least 2 images to analyze')
            return

        self.queue = Queue() # image pair queue
        # runtime n^2
        for i in images:
            for j in images:
                if i != j:
                    self.queue.put((i, j))

        self.results_table.grid_forget()  # clear all previous results
        for item in self.results_table.get_children(''):
            self.results_table.delete(item)

        self.status_var.set('Beginning...')
        self.status_label.pack(side=BOTTOM, fill=BOTH, expand=True)
        self.progressbar.config(value=0.0, maximum=self.queue.qsize())
        self.progressbar.pack(side=BOTTOM, fill=BOTH, expand=True)
        self.browse_button.state(['disabled'])
        self.search_button.state(['disabled'])

        self.master.after(10, self.process_queue) # tkinter to update GUI time: 10 seconds

    def process_queue(self):
        # retrieve path, image path, and images
        pair = self.queue.get()
        original_image = Image.open(os.path.join(self.path, pair[0]))
        subset_image = Image.open(os.path.join(self.path, pair[1]))

        # check if subset image is larger than original in size
        # if so then resize
        if (subset_image.size[0] < original_image.size[0]) and (subset_image.size[1] < original_image.size[1]):
            # check to see if additional resizing is necessary
            if (original_image.size[0] > max_length) or (original_image.size[1] > max_width):
                ratio = min(max_length / float(original_image.size[0]), max_width / float(original_image.size[1]))

                # resize based on ration
                # ANTIALIAS for highest quality downsizing
                original_image = original_image.resize((int(ratio * original_image.size[0]),
                                                        int(ratio * original_image.size[1])),
                                                       Image.ANTIALIAS)
                subset_image = subset_image.resize((int(ratio * subset_image.size[0]),
                                                        int(ratio * subset_image.size[1])),
                                                       Image.ANTIALIAS)

            # no sizing problems occur
            else:
                ratio = 1 # no resize required

            # convert images to gray scale
            # convert images into 2D arrays using numpy
            original_array = np.array(original_image.convert(mode = 'L'))
            subset_array = np.array(subset_image.convert(mode = 'L'))

            # represent the cross representation of the two arrays
            match_array = match_template(original_array, subset_array)
            # find the coordinates of the best match between images
            match_location = np.unravel_index(np.argmax(match_array), match_array.shape)

            # if images were resized, obtain originals to calculate crop coordinates
            if (ratio != 1):
                match_location = (int(match_location[0] / ratio), int(match_location[1] / ratio))

                # obtain original images
                original_image = Image.open(os.path.join(self.path, pair[0]))
                subset_image = Image.open(os.path.join(self.path, pair[1]))

            # index and obtain the subsection of the original image
            original_image_sub_array  = np.array(original_image)[match_location[0] :
                                                                 match_location[0] + subset_image.size[0],
                                                                match_location[1] :
                                                                match_location[1] + subset_image.size[1]]
            original_image_subsection = Image.fromarray(original_image_sub_array, mode = "RGB")

            # calculate the rms difference between the images and obtain the difference in images
            histogram_difference = ImageChops.difference(original_image_subsection, subset_image).histogram()
            square_sum = sum(value * ((index % 256) ** 2) for index, value in enumerate(histogram_difference))
            rms = sqrt(square_sum / float(subset_image.size[0] * subset_image.size[1]))

            # add matches to the table
            if RMS > rms:
                self.results_table.grid(row = 3, column = 0, columnspan = 2, padx = 5, pady = 5)
                self.results_table.insert('', 'end', str(self.progress_var.get()), text = pair[0])
                self.results_table.set(str(self.progress_var.get()), 'subset', pair[1])
                self.results_table.config(height = len(self.results_table.get_children('')))

        self.progressbar.step()
        self.status_var.set("Analyzed {} vs {} - {} pairs remaining...".format(pair[0], pair[1], self.queue.qsize()))

        if not self.queue.empty():
            self.master.after(10, self.process_queue)
        else:
            self.progressbar.pack_forget()
            self.browse_button.state(['!disabled'])
            self.search_button.state(['!disabled'])
            elapsed_time = time() - self.start_time
            self.status_var.set("Task finished. Elapsed Time: {0:.2f} seconds".format(elapsed_time))

# main function
def main():
    root = Tk()
    imageAnalysis(root)
    root.mainloop()

if __name__ == '__main__':
    main()

