import ttk
import Tkinter
import tkFont

from glyxtoolms.gui import AnnotatedPlot
from glyxtoolms.gui import Appearance
import glyxtoolms


"""
class Annotation(object):

    def __init__(self):
        self.x1 = 0
        self.x2 = 0
        self.y = 0
        self.text = ""
        self.items = {}
        self.selected = ""
"""

class SpectrumView(AnnotatedPlot.AnnotatedPlot):

    def __init__(self, master, model):
        AnnotatedPlot.AnnotatedPlot.__init__(self, master, model, xTitle="m/z",
                                     yTitle="Intensity [counts]")

        self.master = master
        self.spec = None # Link to raw spectrum
        self.spectrum = None # Link to current spectrum score

        #self.peaksByItem = {}
        self.clearAnnotatableList()

        self.annotationItems = {}
        self.annotations = {}
        self.currentAnnotation = None
        self.referenceMass = 0

        self.canvas.bind("<Button-2>", self.button2, "+")
        self.canvas.bind("a", self.generateSeries, "+")
        self.font = tkFont.Font(family="Arial",size=12)
        

        #self.canvas.bind("<Button-1>", self.button1Pressed, "+")
        #self.canvas.bind("<ButtonRelease-1>", self.button1Released, "+")
        #self.canvas.bind("<B1-Motion>", self.button3Motion, "+")


        #self.canvas.bind("<Button-3>", self.button3Pressed, "+")
        #self.canvas.bind("<ButtonRelease-3>", self.button3Released, "+")
        #self.canvas.bind("<B3-Motion>", self.button3Motion, "+")

        #self.canvas.bind("<Delete>", self.deleteAnnotation, "+")
        
    def generateSeries(self, event):
        self.model.currentAnalysis.spectraIds[self.spec.getNativeID()].annotations = {}
        self.annotations = self.model.currentAnalysis.spectraIds[self.spec.getNativeID()].annotations
        masses = (glyxtoolms.masses.GLYCAN["HEXNAC"],
                  glyxtoolms.masses.GLYCAN["HEX"],
                  glyxtoolms.masses.GLYCAN["DHEX"],
                  glyxtoolms.masses.GLYCAN["NEUAC"]
                  )
        tolerance = 0.1
        cutoff = 500
        found = {}

        for p1 in self.peaksByItem.values():
            if p1.x < cutoff:
                continue
            for p2 in self.peaksByItem.values():
                if p2.x < cutoff:
                    continue
                diff = p2.x - p1.x
                for charge in range(1,3):
                    for mass in masses:
                        if abs(diff-mass/charge) < tolerance:
                            a = glyxtoolms.io.Annotation()
                            a.x1 = p1.x
                            a.x2 = p2.x
                            a.text = ""
                            a.y = p1.y+p2.y
                            found[charge] = found.get(charge, []) + [a]
                            #self.addAnnotation(a, str(charge))
        for charge in found:
            masses = {}
            for a in found[charge]:
                masses[a.x1] = masses.get(a.x1, []) + [a]
                masses[a.x2] = masses.get(a.x2, []) + [a]
            
            graphs = []
            current = None
            visited = set()
            for mass in masses:
                if mass not in visited:
                    current = mass
                    break
            working = {current}
            graph = set()
            while len(working) > 0:
                current = working.pop()
                if current in visited:
                    continue
                visited.add(current)
                graph.add(current)
                for a in masses[current]:
                    working.add(a.x1)
                    working.add(a.x2)
            graphs.append(graph)
            
            graphs = sorted(graphs, key=lambda g: len(g),reverse=True)
            
            for graph in graphs[:1]:
                show = set()
                for mass in graph:
                    for a in masses[mass]:
                        show.add(a)
                for a in show:
                    self.addAnnotation(a, str(charge))
            
        
        ## keep 10 highest with best connections
        #for charge in found:
        #    conn = {}
        #    for a in found[charge]:
        #        conn[a.x1] = conn.get(a.x1, []) + [a]
        #        conn[a.x2] = conn.get(a.x2, []) + [a]
        #    
        #    keep = {}
        #    for mass in conn:
        #        summ = 0.0
        #        for a in conn[mass]:
        #            summ += a.y
        #        keep[mass] = summ
        #    
        #    keep_keys = sorted(keep, key=lambda mass: keep[mass], reverse=True)
        #    
        #    
        #    #conn_keys = sorted(conn.keys(), key=lambda mass: len(conn[mass]), reverse=True)
        #    show = set()
        #    for mass in keep_keys[:3]:
        #        print mass, conn[mass]
        #        for a in conn[mass]:
        #            show.add(a)
        #    for a in show:
        #        self.addAnnotation(a, str(charge))
            
        self._paintCanvas()

    def identifier(self):
        return "SpectrumView"

    def initSpectrum(self, spec):
        if spec == None:
            return
        if spec.getNativeID() in self.model.currentAnalysis.spectraIds:
             self.annotations = self.model.currentAnalysis.spectraIds[spec.getNativeID()].annotations
        self.spec = spec
        self.referenceMass = 0
        #self.peaksByItem = {}
        self.clearAnnotatableList()
        self.annotationItems = {}
        self.currentAnnotation = None
        self.initCanvas()

    def setMaxValues(self):
        self.aMax = -1
        self.bMax = -1

        for peak in self.spec:
            mz = peak.getMZ()
            intens = peak.getIntensity()
            if self.aMax == -1 or mz > self.aMax:
                self.aMax = mz
            if self.bMax == -1  or intens > self.bMax:
                self.bMax = intens
        self.aMax *= 1.1
        self.bMax *= 1.2

    def paintObject(self):
        if self.spec == None:
            return
        specId = self.spec.getNativeID()
        pInt0 = self.convBtoY(self.viewYMin)

        # create peaklist
        peaks = []
        for peak in self.spec:
            mz = peak.getMZ()
            intens = peak.getIntensity()
            if mz < self.viewXMin or mz > self.viewXMax:
                continue
            if intens < self.viewYMin:
                continue
            peaks.append(AnnotatedPlot.Annotatable(mz,intens))

        # sort peaks after highest intensity
        peaks.sort(reverse=True, key=lambda p: p.y)

        # get scored peaks
        scored = {}
        if specId in self.model.currentAnalysis.spectraIds:
            ions = self.model.currentAnalysis.spectraIds[specId].ions
            for sugar in ions:
                for fragment in ions[sugar]:
                    mass = ions[sugar][fragment]["mass"]
                    l = []
                    for p in peaks:
                        if abs(p.x-mass) < 1.0:
                            l.append((abs(p.x-mass), p.x, sugar, fragment))

                    l.sort()
                    if len(l) > 0:
                        err, mz, sugar, fragment = l[0]
                        scored[mz] = (sugar, fragment)

        scoredPeaks = []
        annotationText = []
        annotationMass = []
        self.clearAnnotatableList()

        for p in peaks:
            # check if peak is a scored peak
            pMZ = self.convAtoX(p.x)
            pInt = self.convBtoY(p.y)
            masstext = str(round(p.x - self.referenceMass, 4))
            if p.x in scored:
                scoredPeaks.append(p)
                sugar, fragment = scored[p.x]
                annotationText.append((pMZ, pInt, fragment, masstext))
            else:
                item = self.canvas.create_line(pMZ, pInt0, pMZ, pInt, tags=("peak", ), fill="black")
                self.addAnnotatableItem(item, p)
                annotationMass.append((pMZ, pInt, "", masstext))

            self.allowZoom = True

        # plot scored peaks last
        scoredPeaks.sort(reverse=True)
        for p in scoredPeaks:
            pMZ = self.convAtoX(p.x)
            pInt = self.convBtoY(p.y)
            item = self.canvas.create_line(pMZ, pInt0, pMZ, pInt, tags=("peak", ), fill="red")
            self.addAnnotatableItem(item, p)

        items = self.plotText(annotationText, set(), 0)
        items = self.plotText(annotationMass, items, 5)

        # paint all available annotations
        self.paintAllAnnotations()

#    def plotText(self, collectedText, items=set(), N=0):
#        # remove text which is outside of view
#        ymax = self.convBtoY(self.viewYMin)
#        ymin = self.convBtoY(self.viewYMax)
#
#        xmin = self.convAtoX(self.viewXMin)
#        xmax = self.convAtoX(self.viewXMax)
#        viewable = []
#        for textinfo in collectedText:
#            x, y, text = textinfo
#            if xmin < x < xmax and ymin < y < ymax:
#                viewable.append(textinfo)
#        # sort textinfo
#        viewable = sorted(viewable, key=lambda t: t[1])
#        # plot items
#
#        for textinfo in viewable:
#            if N > 0 and len(items) >= N:
#                break
#            x, y, text = textinfo
#            item = self.canvas.create_text((x, y, ),
#                                           text=text,
#                                           fill="blue violet",
#                                           anchor="s", justify="center")
#            # check bounds of other items
#            bbox = self.canvas.bbox(item)
#            overlap = set(self.canvas.find_overlapping(*bbox))
#            if len(overlap.intersection(items)) == 0:
#                items.add(item)
#            else:
#                self.canvas.delete(item)
#        return items

    def plotText(self, collectedText, items=set(), N=0):
        """ Draw text items onto the canvas, without overlap.
            Parameters are the collectedText a List of (x, y, text),
            a set of previously drawn items, and the maximum amount of
            items to be drawn (0 - draw as many as possible)"""
        # remove text which is outside of view
        ymax = self.convBtoY(self.viewYMin)
        ymin = self.convBtoY(self.viewYMax)

        xmin = self.convAtoX(self.viewXMin)
        xmax = self.convAtoX(self.viewXMax)
        viewable = []
        for textinfo in collectedText:
            x, y, namedText, massText = textinfo
            if xmin < x < xmax and ymin < y < ymax:
                viewable.append(textinfo)
        # sort textinfo
        viewable = sorted(viewable, key=lambda t: t[1])
        # plot items
        for textinfo in viewable:
            if N > 0 and len(items) >= N:
                break
            x, y, namedText, massText = textinfo
            text = []
            text.append(namedText)
            text.append(massText)
            text = "\n".join(text)
            splitText = text.split("\n")[::-1]
            tempItems = set()
            hasOverlap = False
            for part in splitText:
                item = self.canvas.create_text((x, y), text=part,
                                               fill="blue violet",
                                               font = self.font,
                                               anchor="s", justify="center")
                tempItems.add(item)

                # check bounds of other items
                bbox = self.canvas.bbox(item)
                y = bbox[1] # set new y value based on now drawn string
                overlap = set(self.canvas.find_overlapping(*bbox))
                if len(overlap.intersection(items)) != 0:
                    hasOverlap = True
                    break
            if hasOverlap == False:
                items = items.union(tempItems)
            else:
                for item in tempItems:
                    self.canvas.delete(item)
        return items

    def button2(self, event):
        if self.spec == None:
            return
        peak = self.findPeakAt(event.x)
        if peak == None:
            self.referenceMass = 0
            self.initCanvas(keepZoom=True)
            return
        self.referenceMass = peak.x
        self.initCanvas(keepZoom=True)
