import sublime
import sublime_plugin
import os
import sys
import re
import time
import urllib.request
from . import html2text
from . import HtmlClipboard
from zlib import crc32
import ctypes.wintypes
from ctypes import windll, create_unicode_buffer, c_void_p, c_uint, c_wchar_p
from .lib.PIL import ImageGrab
from .lib.PIL import ImageFile
from .lib.PIL import Image

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

DragQueryFile = ctypes.windll.shell32.DragQueryFileW
DragQueryFile.argtypes = [c_void_p, c_uint, c_wchar_p, c_uint]

GlobalLock = ctypes.windll.kernel32.GlobalLock
GlobalLock.argtypes = [c_void_p]
GlobalLock.restype = c_void_p

GlobalUnlock = ctypes.windll.kernel32.GlobalUnlock
GlobalUnlock.argtypes = [c_void_p]

GlobalSize = ctypes.windll.kernel32.GlobalSize
GlobalSize.argtypes = ctypes.wintypes.HGLOBAL,
GlobalSize.restype = ctypes.c_size_t


ORDER_LIST_PATTERN = re.compile(r"(\s*)(\d+)(\.\s+)\S+")
UNORDER_LIST_PATTERN = re.compile(r"(\s*[-+\**]+)(\s+)\S+")
EMPTY_LIST_PATTERN = re.compile(r"(\s*([-+\**]|\d+\.+))\s+$")


class test(sublime_plugin.TextCommand):
    def run(self,edit):
        print("TEST")

        self.settings = sublime.load_settings('markdownwriter.sublime-settings')
        # get the image save dirname
        self.image_dir_name = self.settings.get('image_dir_name', None)
        if len(self.image_dir_name) == 0:
            self.image_dir_name = None

        # get filename
        view = self.view
        filename = view.file_name()
        # create dir in current path with the name of current filename
        dirname, fileext = os.path.splitext(filename)

        # create new image file under currentdir/filename_without_ext/filename_without_ext%d.png
        fn_without_ext = os.path.basename(dirname)
        if self.image_dir_name is not None:
            subdir_name = os.path.join(os.path.split(dirname)[0], self.image_dir_name)
        else:
            subdir_name = dirname
        if not os.path.lexists(subdir_name):
            os.mkdir(subdir_name)

        if IsClipboardFormatAvailable(CF_DIB):

            OpenClipboard(0)
            try:
                hBITMAP = GetClipboardData(CF_BITMAP)
                hDIBV5 = GetClipboardData(CF_DIBV5)
                sDIBV5 = GlobalSize(hDIBV5)
                hDIB = GetClipboardData(CF_DIB)
                pDIB = GlobalLock(hDIB)
                sDIB = GlobalSize(hDIB)
                # print(pDIB, hex(sDIB))
                if pDIB and sDIB:
                    raw_data = ctypes.create_string_buffer(sDIB)
                    ctypes.memmove(raw_data, pDIB, sDIB)
                    # print(raw_data[0:31])
                    imagehash = crc32(raw_data)
                else:
                    return
                GlobalUnlock(hDIB)
            finally:
                CloseClipboard()

            # relative file path
            rel_filename = os.path.join(
                "%s/%d.png" % (self.image_dir_name if self.image_dir_name else fn_without_ext, imagehash))
            # absolute file path
            abs_filename = os.path.join(subdir_name, "%d.png" % (imagehash))

            im = ImageGrab.grabclipboard()
            im.save(abs_filename, 'PNG')
            for pos in view.sel():
                if 'text.html.markdown' in view.scope_name(pos.begin()):
                    view.insert(edit, pos.begin(), "![](%s)" % rel_filename)
                else:
                    view.insert(edit, pos.begin(), "%s" % rel_filename)


class SmartListCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        for region in self.view.sel():
            line_region = self.view.line(region)
            # the content before point at the current line.
            before_point_region = sublime.Region(line_region.a,region.a)
            before_point_content = self.view.substr(before_point_region)

            # Disable smart list when folded.
            folded = False
            for i in self.view.folded_regions():
                if i.contains(before_point_region):
                    self.view.insert(edit, region.a, '\n')
                    folded = True
            if folded:
                break

            match = EMPTY_LIST_PATTERN.match(before_point_content)
            if match:
                self.view.erase(edit, before_point_region)
                break

            match = ORDER_LIST_PATTERN.match(before_point_content)
            if match:
                insert_text = match.group(1) + \
                              str(int(match.group(2)) + 1) + \
                              match.group(3)
                self.view.insert(edit, region.a, "\n" + insert_text)
                break

            match = UNORDER_LIST_PATTERN.match(before_point_content)
            if match:
                insert_text = match.group(1) + match.group(2)
                self.view.insert(edit, region.a, "\n" + insert_text)
                break

            self.view.insert(edit, region.a, '\n')
        self.adjust_view()

    def adjust_view(self):
        for region in self.view.sel():
            self.view.show(region)




class Html2mdCommand(sublime_plugin.TextCommand):

    def run(self, edit):

        self.settings = sublime.load_settings('markdownwriter.sublime-settings')
        # get the image save dirname
        self.image_dir_name = self.settings.get('image_dir_name', None)
        if len(self.image_dir_name) == 0:
            self.image_dir_name = None

        # get filename
        view = self.view
        filename = view.file_name()
        # create dir in current path with the name of current filename
        dirname, fileext = os.path.splitext(filename)

        # create new image file under currentdir/filename_without_ext/filename_without_ext%d.png
        fn_without_ext = os.path.basename(dirname)
        if self.image_dir_name is not None:
            subdir_name = os.path.join(os.path.split(dirname)[0], self.image_dir_name)
        else:
            subdir_name = dirname
        if not os.path.lexists(subdir_name):
            os.mkdir(subdir_name)

        # ss = HtmlClipboard.GetCfHtml()
        # if IsClipboardFormatAvailable(ss):
        #     continue

        if HtmlClipboard.HasHtml():
            HTML = HtmlClipboard.GetHtml()
            text = html2text.html2text(HTML)
            if text != None:
                for region in self.view.sel():
                    self.view.insert(edit, region.a, text)

                self.r2l = self.settings.get('remoteimage_as_localimage', None)
                if self.r2l == "true":
                    start = time.time()

                    inlineimage = self.view.find_by_selector('markup.underline.link.image.markdown')
                    aa=0
                    for region in reversed(inlineimage):
                        url = self.view.substr(region)

                        if url.startswith(('https://', 'http://')) and url.find(('/ckeditor/'))<0:
                            try:
                                if aa==0:
                                    bb=region.a
                                aa=aa+1

                                req = urllib.request.Request(url, data=None, headers={"User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36"})
                                with urllib.request.urlopen(req) as f:
                                    mybytes = f.read()
                                    imagehash = str(crc32(mybytes))

                                    if f.getheader("Content-Type")=="image/png":
                                        output = open(subdir_name+"/"+imagehash+".png","wb")
                                        output.write(mybytes)
                                        output.close()
                                        self.view.replace(edit,region, self.image_dir_name+"/"+imagehash+'.png "'+url+'"')
                                    elif f.getheader("Content-Type")=="image/jpeg":
                                        output = open(subdir_name+"/"+imagehash+".jpg","wb")
                                        output.write(mybytes)
                                        output.close()
                                        self.view.replace(edit,region, self.image_dir_name+"/"+imagehash+'.jpg "'+url+'"')
                                    elif f.getheader("Content-Type")=="image/gif":
                                        output = open(subdir_name+"/"+imagehash+".gif","wb")
                                        output.write(mybytes)
                                        output.close()
                                        self.view.replace(edit,region, self.image_dir_name+"/"+imagehash+'.gif "'+url+'"')
                                    popup=str(aa)+"<a> Images download</a>"
                                    view.show_popup(popup, flags=sublime.HIDE_ON_MOUSE_MOVE_AWAY, location=bb, max_width=1500, max_height=500)
                            except (urllib.error.HTTPError, urllib.error.URLError) as e:
                                print("url error:",e)
                            finally:
                                f.close()
                    end = time.time()

                    # delete icons ![](http://www.xxx.com/Shared/ckeditor/plugins/SgFile/images/docx.png
                    regexp2 = "!\[.*?]\(.*/ckeditor/(.*?\))"
                    regions2 = self.view.find_all(regexp2)
                    for region in  reversed(regions2) :
                        self.view.erase(edit, region)

                    regexp3 = "\r"
                    regions3 = self.view.find_all(regexp3)
                    for region in  reversed(regions3) :
                        self.view.erase(edit, region)

                    regexp4 = "\n\n\n"
                    regions4 = self.view.find_all(regexp4)
                    for region in  reversed(regions4) :
                        self.view.replace(edit, region, '\n\n')



        elif IsClipboardFormatAvailable(CF_TEXT):
            self.view.run_command('paste')



        # copy image file list and insert into MD
        elif IsClipboardFormatAvailable(CF_HDROP):
            # get clipboard files path list
            file_list = []
            OpenClipboard(0)
            try:
                FilesHandle=GetClipboardData(CF_HDROP)
                hDrop = GlobalLock(FilesHandle)
                count = DragQueryFile(hDrop, 0xFFFFFFFF, None, 0)
                for i in range(count):
                    length = DragQueryFile(hDrop, i, None, 0)
                    buffer = create_unicode_buffer(length)
                    DragQueryFile(hDrop, i, buffer, length + 1)
                    file_list.append(buffer.value)
                GlobalUnlock(FilesHandle)
            finally:
                CloseClipboard()

            lenfile=len(file_list)

            filelist=""
            if lenfile>0:
                for i in range(0, lenfile):
                    fn=file_list[i]
                    if fn.split(".")[-1] in ("png" , "jpg", "jpeg", "gif"):
                        infile = open(fn,"rb")
                        infilebuffer=infile.read()
                        outfile= open(subdir_name+"\\"+str(crc32(infilebuffer))+"."+fn.split(".")[-1], "wb")
                        outfile.write(infilebuffer)
                        infile.close()
                        outfile.close()
                        filelist=filelist+"![]("+self.image_dir_name+"/"+str(crc32(infilebuffer))+"."+fn.split(".")[-1]+")\n\n"
                for region in self.view.sel():
                    self.view.insert(edit, region.a, filelist)



        elif IsClipboardFormatAvailable(CF_DIB):

            OpenClipboard(0)
            try:
                hBITMAP = GetClipboardData(CF_BITMAP)
                hDIBV5 = GetClipboardData(CF_DIBV5)
                sDIBV5 = GlobalSize(hDIBV5)
                hDIB = GetClipboardData(CF_DIB)
                pDIB = GlobalLock(hDIB)
                sDIB = GlobalSize(hDIB)
                # print(pDIB, hex(sDIB))
                if pDIB and sDIB:
                    raw_data = ctypes.create_string_buffer(sDIB)
                    ctypes.memmove(raw_data, pDIB, sDIB)
                    # print(raw_data[0:31])
                    imagehash = crc32(raw_data)
                else:
                    return
                GlobalUnlock(hDIB)
            finally:
                CloseClipboard()

            # relative file path
            rel_filename = os.path.join(
                "%s/%d.png" % (self.image_dir_name if self.image_dir_name else fn_without_ext, imagehash))
            # absolute file path
            abs_filename = os.path.join(subdir_name, "%d.png" % (imagehash))

            im = ImageGrab.grabclipboard()
            im.save(abs_filename, 'PNG')
            for pos in view.sel():
                if 'text.html.markdown' in view.scope_name(pos.begin()):
                    view.insert(edit, pos.begin(), "![](%s)" % rel_filename)
                else:
                    view.insert(edit, pos.begin(), "%s" % rel_filename)


    def is_enabled(self):
        # get filename
        view = self.view
        filename = view.file_name()
        # create dir in current path with the name of current filename
        dirname, fileext = os.path.splitext(filename)
        if fileext.lower()==(".md") or fileext.lower()==(".markdown"):
            return True
        else:
            return False

    def is_visible(self):
        # get filename
        view = self.view
        filename = view.file_name()
        # create dir in current path with the name of current filename
        dirname, fileext = os.path.splitext(filename)
        if fileext.lower()==(".md") or fileext.lower()==(".markdown"):
            return True
        else:
            return False

class BoldCommand(sublime_plugin.TextCommand):

    def run(self, edit):
        selection = self.view.sel()
        for region in selection:
            region_text = self.view.substr(region)
            if len(region_text) > 3 and region_text[0:2] == "**" and region_text[len(region_text) - 2:len(region_text)] == "**":
                self.view.replace(edit, region, region_text[2:len(region_text) - 2])
            else:
                self.view.replace(edit, region, '**' + region_text + '**')


class ItalicCommand(sublime_plugin.TextCommand):

    def run(self, edit):
        selection = self.view.sel()
        for region in selection:
            region_text = self.view.substr(region)
            if len(region_text) > 1 and region_text[0:1] == "_" and region_text[len(region_text) - 1:len(region_text)] == "_":
                self.view.replace(edit, region, region_text[1:len(region_text) - 1])
            else:
                self.view.replace(edit, region, '_' + region_text + '_')


class Head2Command(sublime_plugin.TextCommand):

    def run(self, edit):
        region = self.view.line(self.view.sel()[0])
        current_line_text = self.view.substr(region)

        if current_line_text[0:2] == '# ':
            self.view.replace(edit, region, '#' + current_line_text)
        if current_line_text[0:3] == '## ':
            self.view.replace(edit, region, current_line_text[
                              3:len(current_line_text)])
        if current_line_text[0:4] == '### ':
            self.view.replace(edit, region, current_line_text[
                              1:len(current_line_text)])
        if current_line_text[0:5] == '#### ':
            self.view.replace(edit, region, '#' +
                              current_line_text[3:len(current_line_text)])
        if current_line_text[0:2] != '# ' and current_line_text[0:3] != '## ' and current_line_text[0:4] != '### ' and current_line_text[0:5] != '#### ':
            self.view.replace(edit, region, '## ' + current_line_text)


class Head3Command(sublime_plugin.TextCommand):

    def run(self, edit):
        region = self.view.line(self.view.sel()[0])
        current_line_text = self.view.substr(region)

        if current_line_text[0:2] == '# ':
            self.view.replace(edit, region, '##' + current_line_text)
        if current_line_text[0:3] == '## ':
            self.view.replace(edit, region, '#' + current_line_text)
        if current_line_text[0:4] == '### ':
            self.view.replace(edit, region, current_line_text[
                              4:len(current_line_text)])
        if current_line_text[0:5] == '#### ':
            self.view.replace(edit, region, '#' +
                              current_line_text[3:len(current_line_text)])
        if current_line_text[0:2] != '# ' and current_line_text[0:3] != '## ' and current_line_text[0:4] != '### ' and current_line_text[0:5] != '#### ':
            self.view.replace(edit, region, '### ' + current_line_text)


class Head4Command(sublime_plugin.TextCommand):

    def run(self, edit):
        region = self.view.line(self.view.sel()[0])
        current_line_text = self.view.substr(region)

        if current_line_text[0:2] == '# ':
            self.view.replace(edit, region, '###' + current_line_text)
        if current_line_text[0:3] == '## ':
            self.view.replace(edit, region, '##' + current_line_text)
        if current_line_text[0:4] == '### ':
            self.view.replace(edit, region, '#' + current_line_text)
        if current_line_text[0:5] == '#### ':
            self.view.replace(edit, region, current_line_text[
                              5:len(current_line_text)])
        if current_line_text[0:2] != '# ' and current_line_text[0:3] != '## ' and current_line_text[0:4] != '### ' and current_line_text[0:5] != '#### ':
            self.view.replace(edit, region, '#### ' + current_line_text)
