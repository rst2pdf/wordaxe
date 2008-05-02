#!/bin/env/python
# -*- coding: iso-8859-1 -*-

__license__="""
   Copyright 2004-2007 Henning von Bargen (henning.vonbargen arcor.de)

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
"""

__version__=''' hyphen.py, V 1.0,  Henning von Bargen, $Revision:  1.0 '''

from copy import copy
SHY = "\xAD".decode("iso-8859-1")

class HyphenationPoint:
    """
    A possible hyphenation point in a HyphenatedWord.
    
    Attributes:
      indx        : The index where to split the word.
      quality     : The quality of this hyphenation point (0=bad,5=average,9=very good).
      nl,sl,nr,sr : Replacement parameters.
      
    Description:
      When we split the word at this hyphenation point,
      we can build the two strings left,right as follows:
      left = word[:pos-nl] + sl
      right = sr + word[pos+nr:]

    Some examples (where q is some quality, i.e. q=5):
    
      The usual case is nl=0,sl="\173",nr=0,sr="".
      In other words, just add a "shy" character to the left string.
      "Lesen" (to read) can be hyphenated as "le-" "sen":
      HyphenationPoint(2,q,0,"\173",0,"")
      
      In some cases, it is not necessary to add the shy character:
      "ABC-Buch" (ABC book) can be hyphenated as "ABC-" "buch":
      HyphenationPoint(4,q,0,"",0,"")
      
      And - especially using the OLD german rules - the case
      nl>0 or nr>0 can occur:
      
      The word "backen" (to bake) can be hyphenated between the "c" and the "k";
      however, the hyphenated version would be "bak-" "ken".
      Thus, the one and only hyphenation point in this word is
      HyphenationPoint(3,q,1,"k"+"\173",0,"")
      
      Another example: According to the old german rules, the word "Schiffahrt"
      is a concatenation of "Schiff" (ship) and "fahrt" (journey).
      The triple "f" is shortened to a double "f".
      But in case of hyphenation, it's three "f"s again: "Schiff-" "fahrt".
      HyphenationPoint(5,q,0,"f"+shy,0,"")
      This could also be expressed as HyphenationPoint(6,q,0,shy,0,"f").
    """
    __slots__ = ["indx","quality","nl","sr","nr","sr"]
    def __init__(self,indx,quality,nl=0,sl=u"",nr=0,sr=u""):
        self.indx = indx
        self.quality = quality
        self.nl = nl
        self.sl = unicode(sl)
        self.nr = nr
        self.sr = unicode(sr)
    def __str__(self):
        return 'HyphP(%d,%d)' % (self.indx,self.quality)
    def __repr__(self):
        return 'HyphenationPoint(%d,%d,%d,%s,%d,%s)' % (self.indx,self.quality,self.nl,`self.sl`,self.nr,`self.sr`)

class HyphenatedWord:
    """
    A hyphenated word.
    
    Attributes:
      word:         the word without hyphenations
      hyphenations: a list containing the possible hyphenation points.
      info:         Information about the hyphenation process.
    
    See also class Hyphenator for an explanation.
    """

    def __init__(self, word, hyphenations=[]):
        "Constructor using the string aWord and a list of hyphenation points."
        assert isinstance(word, unicode)
        self.word = word
        self.hyphenations = hyphenations[:]
            
    def __str__(self):
        return ("HyphWord(%s)" % self.word)

    def __repr__(self):
        return ("HyphenatedWord(%r)" % self.word)

    def split(self, hp):
        """Performs a split at the given hyphenation point.
        
           Returns a tuple (left,right)
           where left is a string (the left part, including the hyphenation character)
           and right is a HyphenatedWord describing the rest of the word.
        """
        left = self.word[:hp.indx-hp.nl]+hp.sl
        assert isinstance(left, unicode)
        right = HyphenatedWord(hp.sr+self.word[hp.indx+hp.nr:])
        shift = hp.indx-hp.nr+len(hp.sr)
        right.hyphenations = [HyphenationPoint(h.indx-shift,h.quality,h.nl,h.sl,h.nr,h.sr)
                              for h in self.hyphenations if h.indx>hp.indx
                             ]
        return (left,right)
            
    def showHyphens(self):
        "Returns the possible hyphenations as a string list, for debugging purposes."
        L = []
        for h in self.hyphenations:
            left,right = self.split(h)
            L.append("%s %s (%d)" % (left,right.word, h.quality))
        return L
        
    def prepend(self, prefix):
        "Prepends a prefix to the word. The hyphenation points are shifted accordingly."
        assert isinstance(prefix, unicode)
        self.word = prefix + self.word
        for hp in self.hyphenations:
            hp.indx += len(prefix)
            
    def append(self, suffix):
        "Appends a suffix to the word. The hyphenation points are shifted accordingly."
        assert isinstance(suffix, unicode)
        self.word += suffix
        # Nothing to to for the hyphenations
        
    @staticmethod 
    def join(*hyphwords):
        """
        Create a new hyphenated word from a list of other hyphenated words.
        a = HyphenatedWord("Vogel")    # Vo-gel
        b = HyphenatedWord("grippe")   # grip-pe
        Inserts a good quality hyphenation point at the boundaries.
        c = HyphenatedWord.join(a,b)
        # Vo-gel=grip-pe.
        """
        if len(hyphwords) == 1:
            hyphwords = hyphwords[0]
        for w in hyphwords:
            assert isinstance(w,HyphenatedWord)
        result = HyphenatedWord(u"".join([w.word for w in hyphwords]))
        hps = result.hyphenations
        offset = 0
        for w in hyphwords:
            for h in w.hyphenations:
                hp = copy(h)
                hp.indx += offset
                hps.append(hp)
            if w is not hyphwords[-1]:
                #print w.word
                if w.word.endswith(u"-") or w.word.endswith(SHY):
                    hps.append(HyphenationPoint(offset+len(w.word), quality=9))
                else:
                    hps.append(HyphenationPoint(offset+len(w.word), quality=9, sl=SHY))
                offset += len(w.word)
        return result            

class Hyphenator:
    """
    Hyphenator serves as the base class for all hyphenation implementation classes.
    
    Some general thoughts about hyphenation follow.
    
    Hyphenation is language specific.
    Hyphenation is encoding specific.
    Hyphenation does not use the context of a word.
    Good Hyphenation enables the reader to read fluently,
    bad hyphenation can make a word hard to read.
    
    Hyphenation is language specific:
    The same word may be valid in several languages,
    and the valid hyphenation points can depend on the language.
    Example: Situation
   
    Hyphenation is encoding specific:
    This is just an implementation detail really,
    however an important one.
    For example, every hyphenation algorithm uses some internal
    encoding scheme, and it should document this scheme.
    How is the input encoding and the output encoding?
    
    Hyphenation does not use the context of the word:
    Surely, it could make sense to "understand" the context.
    There may be some words that should be hyphenated differently
    depending on the context.
    But this would make a really BIG overhead;
    and I can't really think of an example. It's not worth thinking about it.
    
    Good Hyphenation enables the reader to read fluently,
    bad hyphenation can make a word hard to read.
    Some languages, for example german, make frequent use of
    the concatenation of several simple words to build more complex words,
    like "Hilberts Nullstellensatz" (something I remember from Algebra).
    Null = Zero
    Stelle = Place, Location
    Satz = Theorem (math)
 
    The one famous example for bad german hyphenation is the word "Urinstinkt".
    This is made up of
    Ur = Primal
    Instinkt = Instinct
   
    These thoughts have led to the following interface for hyphenation.
    """
   
    def __init__ (self, language, minWordLength=4, codec=None, shy=SHY):
        """
        Creates a new hyphenator instance for the given language.
        In this base class, the language arguments serves only for
        information purposes.
        Words shorter than minWordLength letters will never be considererd 
        for hyphenation.
        """
        self.language = language
        self.minWordLength = 4
        assert isinstance(shy, unicode)
        self.shy = shy
        
        """
        self.codec = codec
        if self.codec is None:
            import encodings.latin_1
            self.codec = encodings.latin_1.Codec()
        """
    """        
    def getCodec(self):
        return self.codec
    """
        
    def getLanguage(self):
        return self.language
        
    def getMinWordLength(self):
        return self.minWordLength
        
    def setMinWordLength(self,nLength):
        if type(nLength)==int and nLength>2 and nLength<100:
            self.minWordLength = nLength
        else:
            raise ValueError, nLength
            
    def __repr__(self):
        #return "%s(%s,%d,%s)" % (str(self.__class__),self.language,self.minWordLength,self.codec)
        return "%s(%s,%d)" % (str(self.__class__),self.language,self.minWordLength)
    
    def postHyphenate(self,hyphenatedWord):
        """This function is called whenever hyphenate has been called.
           It can be used to do some logging,
           or to add unknown words to a dictionary etc.
        """
        if hyphenatedWord is not None:
            assert isinstance(hyphenatedWord, HyphenatedWord)
            assert type(hyphenatedWord.hyphenations) == list
            for hp in hyphenatedWord.hyphenations:
                assert isinstance(hp,HyphenationPoint)
                
    def i_hyphenate(self, aWord):
        """
        This base class does not support any hyphenation!
        """
        return None
            
    def hyphenate(self,aWord):
        """
        Finds possible hyphenation points for a aWord, returning a HyphenatedWord
        or None if the hyphenator doesn't know the word.
        """
        assert isinstance(aWord,unicode)
        hword = self.i_hyphenate(aWord)
        self.postHyphenate(hword)
        return hword
