import ttk
import tkFont
import Tkinter
import re
import os
import tkFileDialog

def parseInternalFragment(name, length):
    match = re.match(r"^y\d+b\d+", name)
    if match == None:
        return None, None
    y, b = match.group()[1:].split("b")
    y = length-int(y)
    b = int(b)
    return y, b

def parseBFragment(name):
    match = re.match(r"^b\d+", name)
    if match == None:
        return None, None
    b = int(match.group()[1:])
    return 0, b

def parseYFragment(name, length):
    match = re.match(r"^y\d+", name)
    if match == None:
        return None, None
    y = length-int(match.group()[1:])
    return y, length


class PeptideCoverageFrame(ttk.Frame):

    def __init__(self, master, model):
        ttk.Frame.__init__(self, master=master)

        self.master = master
        self.model = model

        self.hit = None
        self.coverage = {}
        self.fragmentCoverage = {}
        self.indexList = set()

        self.height = 0
        self.width = 0
        
        self.rowconfigure(0, weight=0, minsize=38)
        self.rowconfigure(1, weight=1)
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=0)
        
        self.canvas = Tkinter.Canvas(self, height=100)
        self.canvas.config(bg="white")
        #self.canvas.grid(row=1, column=0, sticky="NSEW")
        #self.canvas.pack(expand=True, fill="both")
        
        self.canvas.config(highlightthickness=0)
        self.canvas.grid(row=1, column=0, sticky="NSEW")



        # Bindings
        self.canvas.bind("<Button-1>", self.eventMouseClick)
        self.canvas.bind("<Configure>", self.on_resize)
        #self.canvas.bind("<Motion>", self.eventMouseMotion, "+")
        self.canvas.bind("<Control-s>", self.savePlot, "+")

        self.menuVar = Tkinter.StringVar(self)
        self.menuVar.trace("w", self.plotSingleFragment)

        self.aMenu = Tkinter.OptionMenu(self, self.menuVar, [])
        self.aMenu.grid(row=0, column=0)
        self.setMenuChoices([])

        # link function
        self.model.registerClass("PeptideCoverageFrame", self)
        
    def plotSingleFragment(self, *args):
        if self.hit == None:
            return
        name = self.menuVar.get()
        if name in self.hit.fragments:
            self.model.classes["ConsensusSpectrumFrame"].plotSelectedFragments([name],zoomIn=True)
        
    def setMenuChoices(self, choices):
        self.aMenu['menu'].delete(0, 'end')
        if len(choices) == 0:
            choice = "no further peptide ions"
            self.menuVar.set(choice)
            self.aMenu['menu'].add_command(label=choice, command=Tkinter._setit(self.menuVar, choice))
            return
        self.menuVar.set(choices[0])
        for choice in choices:
            self.aMenu['menu'].add_command(label=choice, command=Tkinter._setit(self.menuVar, choice))
        # clear
        self.model.classes["ConsensusSpectrumFrame"].plotSelectedFragments([],zoomIn=False)
    
    #def eventMouseMotion(self, event):
    #    self.canvas.focus_set()
    
    def savePlot(self, event):
        if self.model.currentAnalysis == None:
            return
        options = {}
        options['filetypes'] = [('post script', '.eps'), ]
        workingdir = os.path.dirname(self.model.currentAnalysis.path)
        options['initialdir'] = workingdir
        options['parent'] = self
        filename = tkFileDialog.asksaveasfilename(**options)
        if filename == "":
            return
        self.canvas.postscript(file=filename, height=self.height, width=self.width)

    def on_resize(self,event):
        self.width = event.width
        self.height = event.height
        #self.canvas.config(width=self.width, height=self.height)
        self.paint_canvas()
        self.colorIndex(zoomIn=False)

    def init(self, hit):
        analysis = self.model.currentAnalysis
        if analysis == None:
            return
        self.hit = hit
        self.indexList = set()
        self.paint_canvas()
        

    def paint_canvas(self):
        
        self.canvas.delete(Tkinter.ALL)
        self.setMenuChoices([])
        if self.hit == None:
            return
        peptideSequence = self.hit.peptide.sequence
        peptideLength = len(peptideSequence)

        parts = {}
        for i in range(0, peptideLength):
            for e in range(i+1, peptideLength+1):
                name = peptideSequence[i:e]
                key = "".join(sorted(name))
                parts[key] = parts.get(key, []) + [name]

        ySeries = set()
        bSeries = set()
        self.fragmentCoverage = {}
        
        restNames = []
        for name in self.hit.fragments:
            y, b = parseInternalFragment(name, peptideLength)
            if y == None:
                y, b = parseBFragment(name)
            else: # ignore internal fragments
                continue
            if y == None:
                y, b = parseYFragment(name, peptideLength)
            if y == None:
                restNames.append(name)
                continue
            ySeries.add(y)
            bSeries.add(b)
            key_y = "y" + str(y)
            key_b = "b" + str(b)
            self.fragmentCoverage[key_y] = self.fragmentCoverage.get(key_y, []) + [name]
            self.fragmentCoverage[key_b] = self.fragmentCoverage.get(key_b, []) + [name]
        
        self.setMenuChoices(restNames)
        
        # remove 0 and len
        if 0 in ySeries:
            ySeries.remove(0)
        if 0 in bSeries:
            bSeries.remove(0)

        if peptideLength in ySeries:
            ySeries.remove(peptideLength)
        if peptideLength in bSeries:
            bSeries.remove(peptideLength)

        # collect positions of glycosylationsites
        glycosites = set()
        for pos, typ in self.hit.peptide.glycosylationSites:
            glycosites.add(pos-self.hit.peptide.start)
            

        # write peptide sequence
        xc = self.width/2.0
        yc = self.height/2.0
        text = self.hit.peptide.sequence

        # find fitting text size
        s = 0
        for s in range(0, self.height-20):
            font = tkFont.Font(family="Courier", size=s)
            if (font.measure(" ")+4)*len(text) > self.width:
                break
            

        s -= 1
        font = tkFont.Font(family="Courier", size=s)
        letterSize = font.measure(" ")+4
        start = xc - letterSize/2.0*(len(text)-1)
        for index, letter in enumerate(text):
            x = start + index*letterSize
            # check if letter is a glycoslyation site
            fillcolor = "black"
            if index in glycosites:
                fillcolor = "red"
            self.canvas.create_text((x, yc, ), text=letter,
                                    font=("Courier", s),
                                    fill=fillcolor,
                                    anchor="center",
                                    justify="center")
            

        # plot lines

        self.coverage = {}
        for index in ySeries:
            x = start + (index-0.5)*letterSize
            color = "black"
            
            item1 = self.canvas.create_line(x, yc,
                                            x, 20,
                                            tags=("site", ),
                                            fill=color)
            item2 = self.canvas.create_line(x, 20,
                                            x+10, 20,
                                            tags=("site", ),
                                            fill=color)
            item3 = self.canvas.create_text((x+5, 10),
                                            text="y"+str(len(text)-index), 
                                            tags=("site", ),
                                            fill=color,
                                            anchor="center",
                                            justify="center")
            self.coverage[item1] = "y" + str(index)
            self.coverage[item2] = "y" + str(index)
            self.coverage[item3] = "y" + str(index)


        for index in bSeries:
            x = start + (index-0.5)*letterSize
            color = "black"
            item1 = self.canvas.create_line(x, yc,
                                            x, self.height-20,
                                            tags=("site", ),
                                            fill=color)
            item2 = self.canvas.create_line(x, self.height-20,
                                            x-10, self.height-20,
                                            tags=("site", ),
                                            fill=color)
            item3 = self.canvas.create_text((x-5, self.height-10),
                                            text="b"+str(index), 
                                            tags=("site", ),
                                            fill=color,
                                            anchor="center",
                                            justify="center")
            self.coverage[item1] = "b" + str(index)
            self.coverage[item2] = "b" + str(index)
            self.coverage[item3] = "b" + str(index)

    def identifier(self):
        return "PeptideCoverageFrame"

    def eventMouseClick(self, event):
        # clear color from all items
        self.canvas.itemconfigure("site", fill="black")

        overlap = set(self.canvas.find_overlapping(event.x-10,
                                                   event.y-10,
                                                   event.x+10,
                                                   event.y+10))

        self.indexList = set()
        for item in overlap:
            if item in self.coverage:
                key = self.coverage[item]
                self.indexList.add(key)
        self.colorIndex(zoomIn=True)

    def colorIndex(self,zoomIn=False):
        found = []
        for index in self.indexList:
            found += self.fragmentCoverage[index]
            for item in self.coverage:
                if self.coverage[item] == index:
                    self.canvas.itemconfigure(item, fill="red")
        self.model.classes["ConsensusSpectrumFrame"].plotSelectedFragments(found,zoomIn=True)


