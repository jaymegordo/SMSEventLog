
try:
    from tkinter import *
    from tkinter.ttk import *
except:
    from Tkinter import *
    from ttk import *
from pandastable.core import Table
from pandastable.data import TableModel
import pandas as pd

class MyTable(Table):
    def __init__(self, parent=None, **kwargs):
        Table.__init__(self, parent, **kwargs)
        return

class MyApp(Frame):
    def __init__(self, parent=None, df=None):
        self.parent = parent
        Frame.__init__(self)
        self.main = self.master
        self.main.geometry('800x600+200+100')
        self.main.title('pandastable examples')
        f = Frame(self.main)
        f.pack(fill=BOTH,expand=1)
        pt = make_table(f, df=df)
        bp = Frame(self.main)
        bp.pack(side=TOP)
        b=Button(bp,text='Test1', command=test1)
        b.pack(side=LEFT,fill=BOTH,)
        b=Button(bp,text='Test2', command=select_test)
        b.pack(side=LEFT,fill=BOTH,)
        b=Button(bp,text='Test3', command=multiple_tables)
        b.pack(side=LEFT,fill=BOTH,)
        return

def make_table(frame, df, **kwds):
    # df = TableModel.getSampleData()
    # df['label'] = df.label.astype('category')
    pt = MyTable(frame, dataframe=df, **kwds )
    pt.show()
    return pt

def test1(df):
    """just make a table"""

    t = Toplevel()
    fr = Frame(t)
    fr.pack(fill=BOTH,expand=1)
    pt = make_table(fr, df=df)
    return

def select_test():
    """cell selection and coloring"""

    t = Toplevel()
    fr = Frame(t)
    fr.pack(fill=BOTH,expand=1)
    pt = Table(fr)
    pt.show()
    pt.importCSV('test.csv', index_col=0)
    pt.resetIndex(ask=False)
    pt.columncolors = {'c':'#fbf1b8'}
    df = pt.model.df
    #rows = pt.getRowsFromMask(mask=mask)
    #pt.multiplerowlist = rows

    mask_1 = df.a<7
    pt.setColorByMask('a', mask_1, '#ff9999')
    colors = {'red':'#f34130','blue':'blue'}
    for l in df.label.unique():
    	mask = df['label']==l
    	pt.setColorByMask('label', mask, l) #colors[l])
    pt.redraw()
    return

def multiple_tables():
    """make many tables in one frame"""

    t = Toplevel(height=800)
    r=0;c=0
    for i in range(6):
        fr = Frame(t)
        fr.grid(row=r,column=c)
        pt = make_table(fr, showtoolbar=False, showstatusbar=True)
        c+=1
        if c>2:
            c=0
            r+=1
    return

# app = MyApp()
# app.mainloop()