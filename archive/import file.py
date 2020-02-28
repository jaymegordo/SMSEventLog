from tkinter import *
from tkinter.filedialog import askopenfilename
from tkinter.messagebox import showerror

from pathlib import Path
import SMS.Folders as fldr

class ImportFile():
    def __init__(self):
        self.root = Tk()
    
    def load(self):
        self.root.filename = Path(askopenfilename())
        fldr.import_fault(self.root.filename)
        # return self.root.filename
    
    def close(self):
        self.root.destroy()
    
    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


class MyFrame(Frame):
    def __init__(self):
        Frame.__init__(self)
        self.master.title("Import Fault CSV")
        # self.load_file()
        # self.master.rowconfigure(5, weight=1)
        # self.master.columnconfigure(5, weight=1)
        # self.grid(sticky=W+E+N+S)

        # self.button = Button(self, text="Browse", command=self.load_file, width=10)
        # self.button.grid(row=1, column=0, sticky=W)

    def load_file(self):
        fname = askopenfilename()
        if fname:
            try:
                return Path(fname)
            except:
                showerror("Open Source File", "Failed to read file\n'%s'" % fname)
        
        self.destroy()
        

