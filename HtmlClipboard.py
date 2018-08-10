"""
Modified on July 10, 2018

@author: vanleo2001

1. The original source will count length of Chinese word incorrectly. So I correct it.
2. For reducing the size of dependency in Sublime Text 3, I replace the library pywin32 with ctypes


original: http://code.activestate.com/recipes/474121/
    # HtmlClipboard
    # An interface to the "HTML Format" clipboard data format

    __author__ = "Phillip Piper (jppx1[at]bigfoot.com)"
    __date__ = "2006-02-21"
    __version__ = "0.1"

"""

import re
import time
import random
import ctypes.wintypes

# Clipboard Formats
CF_TEXT = 1
CF_BITMAP = 2
CF_METAFILEPICT = 3
CF_SYLK = 4
CF_DIF = 5
CF_TIFF = 6
CF_OEMTEXT = 7
CF_DIB = 8
CF_PALETTE = 9
CF_PENDATA = 10
CF_RIFF = 11
CF_WAVE = 12
CF_UNICODETEXT = 13
CF_ENHMETAFILE = 14
CF_HDROP = 15
CF_LOCALE = 16
CF_DIBV5 = 17
CF_MAX = 18
CF_OWNERDISPLAY = 0x0080
CF_DSPTEXT = 0x0081
CF_DSPBITMAP = 0x0082
CF_DSPMETAFILEPICT = 0x0083
CF_DSPENHMETAFILE = 0x008E
CF_PRIVATEFIRST = 0x0200
CF_PRIVATELAST = 0x02FF
CF_GDIOBJFIRST = 0x0300
CF_GDIOBJLAST = 0x03FF

RegisterClipboardFormat = ctypes.windll.user32.RegisterClipboardFormatW
RegisterClipboardFormat.argtypes = ctypes.wintypes.LPWSTR,
RegisterClipboardFormat.restype = ctypes.wintypes.UINT
CF_HTML = RegisterClipboardFormat('HTML Format')

EnumClipboardFormats = ctypes.windll.user32.EnumClipboardFormats
EnumClipboardFormats.argtypes = ctypes.wintypes.UINT,
EnumClipboardFormats.restype = ctypes.wintypes.UINT

GetClipboardData = ctypes.windll.user32.GetClipboardData
GetClipboardData.argtypes = ctypes.wintypes.UINT,
GetClipboardData.restype = ctypes.wintypes.HANDLE

SetClipboardData = ctypes.windll.user32.SetClipboardData
SetClipboardData.argtypes = ctypes.wintypes.UINT, ctypes.wintypes.HANDLE
SetClipboardData.restype = ctypes.wintypes.HANDLE

OpenClipboard = ctypes.windll.user32.OpenClipboard
OpenClipboard.argtypes = ctypes.wintypes.HANDLE,
OpenClipboard.restype = ctypes.wintypes.BOOL

IsClipboardFormatAvailable = ctypes.windll.user32.IsClipboardFormatAvailable

CloseClipboard = ctypes.windll.user32.CloseClipboard
CloseClipboard.restype = ctypes.wintypes.BOOL

#---------------------------------------------------------------------------
#  Convenience functions to do the most common operation

def HasHtml():
    """
    Return True if there is a Html fragment in the clipboard..
    """
    cb = HtmlClipboard()
    return cb.HasHtmlFormat()


def GetHtml():
    """
    Return the Html fragment from the clipboard or None if there is no Html in the clipboard.
    """
    cb = HtmlClipboard()
    if cb.HasHtmlFormat():
        return cb.GetFragment()
    else:
        return None


def PutHtml(fragment):
    """
    Put the given fragment into the clipboard.
    Convenience function to do the most common operation
    """
    cb = HtmlClipboard()
    cb.PutFragment(fragment)


def GetCfHtml():
    """
    Return the FORMATID of the HTML format
    """
    global CF_HTML
    if CF_HTML is None:
        CF_HTML = RegisterClipboardFormat("HTML Format")

    return CF_HTML


#---------------------------------------------------------------------------

class HtmlClipboard:

    CF_HTML = None

    MARKER_BLOCK_OUTPUT = \
        "Version:1.0\r\n" \
        "StartHTML:%09d\r\n" \
        "EndHTML:%09d\r\n" \
        "StartFragment:%09d\r\n" \
        "EndFragment:%09d\r\n" \
        "StartSelection:%09d\r\n" \
        "EndSelection:%09d\r\n" \
        "SourceURL:%s\r\n"

    MARKER_BLOCK_EX = \
        "Version:(\S+)\s+" \
        "StartHTML:(\d+)\s+" \
        "EndHTML:(\d+)\s+" \
        "StartFragment:(\d+)\s+" \
        "EndFragment:(\d+)\s+" \
        "StartSelection:(\d+)\s+" \
        "EndSelection:(\d+)\s+" \
        "SourceURL:(\S+)"
    MARKER_BLOCK_EX_RE = re.compile(MARKER_BLOCK_EX)

    MARKER_BLOCK = \
        "Version:(\S+)\s+" \
        "StartHTML:(\d+)\s+" \
        "EndHTML:(\d+)\s+" \
        "StartFragment:(\d+)\s+" \
        "EndFragment:(\d+)\s+" \
           "SourceURL:(\S+)"
    MARKER_BLOCK_RE = re.compile(MARKER_BLOCK)

    DEFAULT_HTML_BODY = \
        "<!DOCTYPE HTML PUBLIC \"-//W3C//DTD HTML 4.0 Transitional//EN\">" \
        "<HTML><HEAD></HEAD><BODY><!--StartFragment-->%s<!--EndFragment--></BODY></HTML>"

    def __init__(self):
        self.html = None
        self.fragment = None
        self.selection = None
        self.source = None
        self.htmlClipboardVersion = None


    def GetCfHtml(self):
        """
        Return the FORMATID of the HTML format
        """
        if self.CF_HTML is None:
            self.CF_HTML = RegisterClipboardFormat("HTML Format")

        return self.CF_HTML


    def GetAvailableFormats(self):
        """
        Return a possibly empty list of formats available on the clipboard
        """
        formats = []
        try:
            OpenClipboard(0)
            cf = EnumClipboardFormats(0)
            while (cf != 0):
                formats.append(cf)
                cf = EnumClipboardFormats(cf)
        finally:
            CloseClipboard()

        return formats



    def HasHtmlFormat(self):
        """
        Return a boolean indicating if the clipboard has data in HTML format
        """
        return (self.GetCfHtml() in self.GetAvailableFormats())


    def GetFromClipboard(self):
        """
        Read and decode the HTML from the clipboard
        """

        # implement fix from: http://teachthe.net/?p=1137

        cbOpened = False
        while not cbOpened:
            try:
                OpenClipboard(0)
                SrcHandle = GetClipboardData(self.GetCfHtml())
                src = ctypes.c_char_p(SrcHandle).value
                src = src.decode("UTF-8")
                self.DecodeClipboardSource(src)

                cbOpened = True

                CloseClipboard()
            except Exception as err:
                # If access is denied, that means that the clipboard is in use.
                # Keep trying until it's available.
                if err.winerror == 5:  # Access Denied
                    pass
                    # wait on clipboard because something else has it. we're waiting a
                    # random amount of time before we try again so we don't collide again
                    time.sleep( random.random()/50 )
                elif err.winerror == 1418:  # doesn't have board open
                    pass
                elif err.winerror == 0:  # open failure
                    pass
                else:
                    print( 'ERROR in Clipboard section of readcomments: %s' % err)

                    pass

    def DecodeClipboardSource(self, src):
        """
        Decode the given string to figure out the details of the HTML that's on the string
        """
        # find inline html correctly, even for Chinese word content
        # print("searchobj")
        searchObj = re.search( r'<!--StartFragment-->(.*)<!--EndFragment-->', src, re.S)
        # if searchObj:
        #     print("group(1) : "+ searchObj.group(1))

        self.fragment =searchObj.group(1)

        # Try the extended format first (which has an explicit selection)
        # matches = self.MARKER_BLOCK_EX_RE.match(src)
        # if matches:
        #     self.prefix = matches.group(0)
        #     self.htmlClipboardVersion = matches.group(1)
        #     self.html = src[int(matches.group(2)):int(matches.group(3))]
        #     self.fragment = src[int(matches.group(4)):int(matches.group(5))]
        #     self.selection = src[int(matches.group(6)):int(matches.group(7))]
        #     self.source = matches.group(8)
        # else:
        #     # Failing that, try the version without a selection
        #     matches = self.MARKER_BLOCK_RE.match(src)
        #     if matches:
        #         self.prefix = matches.group(0)
        #         self.htmlClipboardVersion = matches.group(1)
        #         self.html = src[int(matches.group(2)):int(matches.group(3))]
        #         self.fragment = src[int(matches.group(4)):int(matches.group(5))]
        #         self.source = matches.group(6)
        #         self.selection = self.fragment


    def GetHtml(self, refresh=False):
        """
        Return the entire Html document
        """
        if not self.html or refresh:
            self.GetFromClipboard()
        return self.html


    def GetFragment(self, refresh=False):
        """
        Return the Html fragment. A fragment is well-formated HTML enclosing the selected text
        """
        if not self.fragment or refresh:
            self.GetFromClipboard()
        return self.fragment


    def GetSelection(self, refresh=False):
        """
        Return the part of the HTML that was selected. It might not be well-formed.
        """
        if not self.selection or refresh:
            self.GetFromClipboard()
        return self.selection


    def GetSource(self, refresh=False):
        """
        Return the URL of the source of this HTML
        """
        if not self.selection or refresh:
            self.GetFromClipboard()
        return self.source


    def PutFragment(self, fragment, selection=None, html=None, source=None):
        """
        Put the given well-formed fragment of Html into the clipboard.

        selection, if given, must be a literal string within fragment.
        html, if given, must be a well-formed Html document that textually
        contains fragment and its required markers.
        """
        if selection is None:
            selection = fragment
        if html is None:
            html = self.DEFAULT_HTML_BODY % fragment
        if source is None:
            source = "file://HtmlClipboard.py"

        fragmentStart = html.index(fragment)
        fragmentEnd = fragmentStart + len(fragment)
        selectionStart = html.index(selection)
        selectionEnd = selectionStart + len(selection)
        self.PutToClipboard(html, fragmentStart, fragmentEnd, selectionStart, selectionEnd, source)


    def PutToClipboard(self, html, fragmentStart, fragmentEnd, selectionStart, selectionEnd, source="None"):
        """
        Replace the Clipboard contents with the given html information.
        """

        try:
            OpenClipboard(0)
            EmptyClipboard()
            src = self.EncodeClipboardSource(html, fragmentStart, fragmentEnd, selectionStart, selectionEnd, source)
            src = src.encode("UTF-8")
            SetClipboardData(self.GetCfHtml(), src)
        finally:
            CloseClipboard()


    def EncodeClipboardSource(self, html, fragmentStart, fragmentEnd, selectionStart, selectionEnd, source):
        """
        Join all our bits of information into a string formatted as per the HTML format specs.
        """
        # How long is the prefix going to be?
        dummyPrefix = self.MARKER_BLOCK_OUTPUT % (0, 0, 0, 0, 0, 0, source)
        lenPrefix = len(dummyPrefix)

        prefix = self.MARKER_BLOCK_OUTPUT % (lenPrefix, len(html)+lenPrefix,
                        fragmentStart+lenPrefix, fragmentEnd+lenPrefix,
                        selectionStart+lenPrefix, selectionEnd+lenPrefix,
                        source)
        return (prefix + html)


def DumpHtml():

    cb = HtmlClipboard()
    print("GetAvailableFormats()=%s" % str(cb.GetAvailableFormats()))
    print("HasHtmlFormat()=%s" % str(cb.HasHtmlFormat()))
    if cb.HasHtmlFormat():
        cb.GetFromClipboard()
        print("prefix=>>>%s<<<END" % cb.prefix)
        print("htmlClipboardVersion=>>>%s<<<END" % cb.htmlClipboardVersion)
        print("GetSelection()=>>>%s<<<END" % cb.GetSelection())
        print("GetFragment()=>>>%s<<<END" % cb.GetFragment())
        print("GetHtml()=>>>%s<<<END" % cb.GetHtml())
        print("GetSource()=>>>%s<<<END" % cb.GetSource())


if __name__ == '__main__':

    def test_SimpleGetPutHtml():
        data = "<p>Writing to the clipboard is <strong>easy</strong> with this code.</p>"
        PutHtml(data)
        if GetHtml() == data:
            print("passed")
        else:
            print("failed")

    test_SimpleGetPutHtml()
    #DumpHtml()
