# -*- coding: utf-8 -*-

# Helper classes for the new Paragraph-Implementation

from copy import copy

import reportlab.pdfbase.pdfmetrics as pdfmetrics
from reportlab.lib.abag import ABag

from wordaxe.hyphen import HyphenationPoint, SHY, HyphenatedWord

class Style(ABag):
    "This is used to store style attributes."

class Fragment(object):
    "A fragment representing a piece of text or other information"
    
class StyledFragment(Fragment):
    def __init__(self, style):
        self.style = style

    @staticmethod
    def str_width(text, style):
        "Compute the width of a styled text"
        return pdfmetrics.stringWidth(text, style.fontName, style.fontSize)

    def __repr__(self):
        return self.__class__.__name__
    __str__ = __repr__
        
class StyledText(StyledFragment):    
    "A string in some style"
    def __init__(self, text, style):
        assert isinstance(text, unicode)
        super(StyledText, self).__init__(style)
        self.text = text
        self.width = self.str_width(text, style)
        cbDefn = getattr(style,"cbDefn", None)
        if cbDefn is not None and not self.width:
            self.width = getattr(cbDefn, "width", 0)
        self.ascent, self.descent = pdfmetrics.getAscentDescent(style.fontName, style.fontSize)

    def __str__(self):
        return "ST(%s)" % self.text.encode("utf-8")
        
    __repr__ = __str__

    @staticmethod
    def fromParaFrag(frag):
        "This allows to reuse the good old paraparser.py"
        text = frag.text
        if not isinstance(text, unicode):
            text = unicode(text, "utf-8")
        return StyledText(text, frag)
        
class StyledWhiteSpace(StyledFragment):
    "Used for every token that delimits words."

class StyledSpace(StyledWhiteSpace):
    "A spacer in some style"
    def __init__(self, style, text=u" "):
        super(StyledSpace, self).__init__(style)
        self.text = unicode(text)
        self.width = self.str_width(text, style)

    def __str__(self):
        return "SP(%s)" % self.text.encode("utf-8")

    __repr__ = __str__
        
class StyledNewLine(StyledWhiteSpace):
    "A new line"

    def __str__(self):
        return "NL"

    __repr__ = __str__

class StyledWord(Fragment):
    "A word compound of some styled strings"

    def __init__(self, fragments):
        for frag in fragments: assert isinstance(frag, StyledText)
        self.fragments = fragments
        # Breite berechnen
        self.text = u"".join([f.text for f in fragments])
        self.width = sum([f.width for f in fragments])
        
    def __str__(self):
        return "SW(%s)" % self.text.encode("utf-8")
        
    __repr__ = __str__
    
    def splitAt(self, hp):
        """
        Splits the styled word at a given hyphenation point
        (see wordaxe.hyphen).
        The result is a tuple (left, right) of StyledWords.
        Works just like HyphenatedWord.split, but for a StyledWord.
        """
        
        #print self, "splitAt", hp
        assert isinstance(self.text, HyphenatedWord)
        # first get the unstyled versions
        ltext, rtext = self.text.split(hp)
        #print "   unstyled would return", ltext, rtext
        if isinstance(hp, int):
            indx = hp
            nl = nr = 0
            sl = SHY
            sr = u""
        else:
            indx = hp.indx
            nl = hp.nl
            nr = hp.nr
            sl = hp.sl
            sr = hp.sr
        lfrags = []
        rfrags = []
        n = 0
        stillLeftPart = True
        firstRight = False
        for frag in self.fragments:
            if not isinstance(frag, StyledText):
                if stillLeftPart:
                    lfrags.append(frag)
                else:
                    rfrags.append(frag)
                continue
            text = frag.text
            if stillLeftPart:
                if len(text) < indx-n:
                    # fragment still before the hyphenation point
                    lfrags.append(frag)
                    n += len(text)
                elif len(text) == indx-n:
                    # fragment boundary exactly at the hyphenation point
                    if nl>0: text = text[:-nl]
                    if sl: text += sl
                    if text is frag.text:
                        lfrags.append(frag)
                    else:
                        lfrags.append(StyledText(text, frag.style))
                    n += len(text)
                    stillLeftPart = False
                    firstRight = True
                else:
                    # fragment crosses the hyphenation point
                    n1 = indx-n
                    tl = text[:n1-nl] + sl
                    tr = sr + text[n1+nr:]
                    lfrags.append(StyledText(tl, frag.style))
                    rfrags.append(StyledText(tr, frag.style))
                    stillLeftPart = False
            elif firstRight and (sr or nr):
                rfrags.append(StyledText(sr + frag.text[nr:], frag.style))
                firstRight = False
            else:
                rfrags.append(frag)
        left = StyledWord(lfrags)
        right = StyledWord(rfrags)
        #print "splitWordAt returns %s, %s" % (left, right)
        assert left.text == ltext
        assert unicode(right.text) == rtext
        right.text = rtext
        return left, right        

        # OLD CODE

        print "left,right=", left, right
        # now restore the styled fragments for left + right
        remaining = self.fragments[:]
        lfrags = list()
        ltext = u""
        rfrags = list()
        rtext = u""
        while remaining and ltext.startswith(ltext + remaining[0].text):
            frag = remaining.pop(0)
            ltext += frag.text
            lfrags.append(frag)
        while remaining and rtext.endswith(remaining[-1].text + rtext):
            frag = remaining.pop(-1)
            rtext = frag.text + rtext
            rfrags.insert(0, frag)
        # Now at most 2 frags might remain.
        # Decide whether they belong to left or right
        assert len(remaining) <= 2, (lfrags, rfrags, remaining)
        if remaining:
            if type(hp) is int:
                indx = hp
            else:
                indx = hp.indx
            lfrags.append(StyledText(left[len(ltext):], remaining[0].style))
            if rtext:
                rfrags.insert(0, StyledText(right[:-len(rtext)], remaining[-1].style))
            else:
                rfrags.insert(0, StyledText(right, remaining[-1].style))
        left = StyledWord(lfrags)
        right = StyledWord(rfrags)
        return (left,right)


class Line(object):
    "A single line in the paragraph"
     
    def __init__(self, fragments, width, height, baseline, space_wasted, keepWhiteSpace):
        for frag in fragments: assert isinstance(frag, Fragment)
        self.fragments = fragments
        self.width = width
        #print fragments
        self.height = height
        self.baseline = baseline
        self.keepWhiteSpace = keepWhiteSpace
        assert 0 <= self.baseline
        assert baseline <= height
        self.space_wasted = space_wasted
        # don't consider WhiteSpace at the start and end of the line
        # for the width calculation
        print_indx_start, print_indx_end = (0, len(self.fragments))
        if not keepWhiteSpace:
            while print_indx_start < len(fragments) \
            and isinstance(fragments[print_indx_start], StyledSpace):
                print_indx_start += 1
            while print_indx_end > print_indx_start \
            and isinstance(fragments[print_indx_end-1], StyledSpace):
                print_indx_end -= 1
            # TODO: What to do with two differently styled spaces 
            #       in the middle of the line?
        self.print_indx_start = print_indx_start
        self.print_indx_end = print_indx_end
        #assert abs(self.width - sum(getattr(f,"width",0) for f in fragments[print_indx_start:print_indx_end])) <= 1e-5
        if not abs(self.width - sum(getattr(f,"width",0) for f in fragments[print_indx_start:print_indx_end])) <= 1e-5:
            print "Assertion failure"
            print "self.width=%f" % self.width
            print "nFrags=%d" % len(fragments)
            print "printrange=%d:%d" % (self.print_indx_start, print_indx_end)
            print "printwidth=%f" % sum(getattr(f,"width",0) for f in fragments[print_indx_start:print_indx_end])
            for i,f in enumerate(fragments): print i, f, getattr(f, "width")

        # Compute font size
        max_size = 0
        max_ascent = min_descent = 0
        for frag in self.iter_flattened_frags():
            if isinstance(frag, StyledText):
                size = getattr(frag.style, "fontSize", 0)
                ascent, descent = frag.ascent, frag.descent
                if not max_size:
                    max_size = size
                    max_ascent = ascent
                    max_descent = descent
                else:
                    max_size = max(max_size, size)
                    max_ascent = max(max_ascent, ascent)
                    min_descent = min(min_descent, descent)
        self.fontSize = max_size
        self.ascent = max_ascent
        self.descent = min_descent
         
    def __str__(self):
        return "Line(%s)" % (",".join(str(frag) for frag in self.fragments))
     
    __repr__ = __str__
    

    def iter_flattened_frags(self):
        """
        Returns the fragments flattened (one word may contribute several fragments).
        """
        return flatten_frags(self.fragments)

    def iter_print_frags(self):
        """
        Returns the fragments (to print) flattened (one word may contribute several fragments).
        """
        return flatten_frags(self.fragments[self.print_indx_start:self.print_indx_end])

def frags_to_StyledFragments(frag_list):
    """
    A helper function for frags_reportlab_to_wordaxe.
    Yields StyledWords, StyledSpace and other entries,   
    """
    for f in frag_list:
        #if hasattr(f, "cbDefn") and f.cbDefn.kind!="img": print "convert", f
        if getattr(f, "lineBreak", False):
            assert not f.text
            yield StyledNewLine(f)
        text = f.text
        del f.text
        if not isinstance(text, unicode):
            text = unicode(text, "utf-8")
        while u" " in text:
            indxSpace = text.find(u" ")
            if indxSpace > 0:
                yield StyledText(text[:indxSpace], f)
            indxNext = indxSpace
            while text[indxNext:].startswith(u" "):
                indxNext += 1
            yield StyledSpace(f) # we ignore repeated blanks
            text = text[indxNext:]
        if text or hasattr(f, "cbDefn"):
            yield StyledText(text, f)
                

def frags_reportlab_to_wordaxe(frags, style):
    """
    Converts an iterator of reportlab frags to wordaxe frags.
    Yields StyledWords, StyledSpace and other entries,
    but StyledTexts are grouped to StyledWords.
    """
    word_frags = []
    for frag in frags_to_StyledFragments(frags):
        if isinstance(frag, StyledText):
            word_frags.append(frag)
        else:
            if word_frags:
                yield StyledWord(word_frags)
                word_frags = []
            yield frag
    if word_frags:
        yield StyledWord(word_frags)

def flatten_frags(frags):
    """
    A helper function that flattens the StyledFragments,
    i.e. StyledWords are split into StyledText fragments.
    """
    for frag in frags:
        if isinstance(frag, StyledWord):
            for f in frag.fragments:
                yield f
        else:
            yield frag
    
def frags_wordaxe_to_reportlab(frags):
    """
    Converts an iterator of wordaxe frags to reportlab frags.
    Fragments of the same style will be joined.
    """
    last_frag = None
    for frag in flatten_frags(frags):
        if last_frag is None or not hasattr(frag,"text") or last_style is not frag.style:
            if last_frag is not None:
                yield last_frag
            last_style = frag.style
            last_frag = copy(frag)
        else:
            last_frag.text += frag.text
            last_frag.width += frag.width
    if last_frag is not None:
        yield last_frag