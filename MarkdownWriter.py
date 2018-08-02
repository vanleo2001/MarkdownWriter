import sublime
import sublime_plugin
import os
import sys
import re
import time
import urllib.request
import imghdr
from . import html2text
from . import HtmlClipboard
from imp import reload
# import hashlib
from zlib import crc32
import ctypes.wintypes
from ctypes import windll, create_unicode_buffer, c_void_p, c_uint, c_wchar_p

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


print(sys.getdefaultencoding())
reload(sys)
# sys.setdefaultencoding('utf-8')

if sys.platform == 'win32':
    package_file = os.path.normpath(os.path.abspath(__file__))
    package_path = os.path.dirname(package_file)
    lib_path = os.path.join(package_path, "lib")
    if lib_path not in sys.path:
        sys.path.append(lib_path)
        print(sys.path)
    from PIL import ImageGrab
    from PIL import ImageFile
    from PIL import Image



ORDER_LIST_PATTERN = re.compile(r"(\s*)(\d+)(\.\s+)\S+")
UNORDER_LIST_PATTERN = re.compile(r"(\s*[-+\**]+)(\s+)\S+")
EMPTY_LIST_PATTERN = re.compile(r"(\s*([-+\**]|\d+\.+))\s+$")


class SmartListCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        for region in self.view.sel():
            line_region = self.view.line(region)
            # the content before point at the current line.
            before_point_region = sublime.Region(line_region.a,
                                                 region.a)
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

class test(sublime_plugin.TextCommand):
    def run(self,edit):
        inlineimage = self.view.find_by_selector('markup.underline.link.image.markdown')
        print('test')
        for region in reversed(inlineimage):
            url = self.view.substr(region)
            print(url)


class Html2mdCommand(sublime_plugin.TextCommand):

    def run(self, edit):
        # get current view width pixel
        # print( self.view.viewport_extent()[0] )
        # get current view  chars numver per line
        # print( self.view.viewport_extent()[0] / self.view.em_width())
        # 读取clipboard的格式
        # im = ImageGrab.grabclipboard()
        # if isinstance(im, Image.Image):
            # print('Image format, size, mode: ', im.format, im.size, im.mode)

        self.settings = sublime.load_settings('markdownwriter.sublime-settings')
        # get the image save dirname
        self.image_dir_name = self.settings.get('image_dir_name', None)
        if len(self.image_dir_name) == 0:
            self.image_dir_name = None

        # get filename
        view = self.view
        filename = view.file_name()
        # create dir in current path with the name of current filename
        dirname, _ = os.path.splitext(filename)

        # create new image file under currentdir/filename_without_ext/filename_without_ext%d.png
        fn_without_ext = os.path.basename(dirname)
        if self.image_dir_name is not None:
            subdir_name = os.path.join(os.path.split(dirname)[0], self.image_dir_name)
        else:
            subdir_name = dirname
        if not os.path.lexists(subdir_name):
            os.mkdir(subdir_name)
        print("image_dir is:", self.image_dir_name, subdir_name)


        # 直接复制image文件并直接插入md中
        if IsClipboardFormatAvailable(CF_HDROP):
            print("paste image file list")

            # get clipboard files path list
            file_list = []
            OpenClipboard(0)
            FilesHandle=GetClipboardData(CF_HDROP)
            hDrop = GlobalLock(FilesHandle)
            count = DragQueryFile(hDrop, 0xFFFFFFFF, None, 0)
            for i in range(count):
                length = DragQueryFile(hDrop, i, None, 0)
                buffer = create_unicode_buffer(length)
                DragQueryFile(hDrop, i, buffer, length + 1)
                file_list.append(buffer.value)
            GlobalUnlock(FilesHandle)
            CloseClipboard()
            # print(file_list)

            lenfile=len(file_list)
            # print("lenfile", lenfile)

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

        elif IsClipboardFormatAvailable(CF_TEXT):
            # OpenClipboard(0)
            # clipboard = GetClipboardData()
            # CloseClipboard()
            print("paste CF_TEXT")

            if HtmlClipboard.HasHtml():
                print("paste html")
            	# HtmlClipboard.DumpHtml()
                HTML = HtmlClipboard.GetHtml()
                text = html2text.html2text(HTML)
                if text != None:
                    for region in self.view.sel():
                        self.view.insert(edit, region.a, text)

                    self.r2l = self.settings.get('remoteimage_as_localimage', None)
                    if self.r2l == "true":
                        # images = []
                        start = time.time()

                        # find inline image regex
                        # a01 = self.view.find_all("(?:!\[(.*?)\]\((.*?)\))")
                        # print('aaa1',self.view.substr(a01[0]))

                        inlineimage = self.view.find_by_selector('markup.underline.link.image.markdown')
                        aa=0
                        for region in reversed(inlineimage):
                        # 从最后一个match开始修改。从前向后修改会导致view的内容改变，进而影响后面match的查找
                            url = self.view.substr(region)

                            if url.startswith(('https://', 'http://')) and url.find(('/ckeditor/'))<0:
                                # images.append(url)
                                try:
                                    # 获取最后一个img url位置，供popup使用
                                    if aa==0:
                                        bb=region.a
                                    aa=aa+1

                                    req = urllib.request.Request(url, data=None, headers={"User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36"})
                                    with urllib.request.urlopen(req) as f:
                                        # print(f.status)
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
                                        # print(imagehash)
                                        popup=str(aa)+"<a> Images download</a>"
                                        view.show_popup(popup, flags=sublime.HIDE_ON_MOUSE_MOVE_AWAY, location=bb, max_width=1500, max_height=500)
                                except (urllib.error.HTTPError, urllib.error.URLError) as e:
                                    print("url error:",e)
                                finally:
                                    f.close()
                                print("Downloading:",url)
                        end = time.time()
                        print("DownloadingImgTime:",end-start)
                        # regexp = "(?<!\[)!\[]\(.*\)]"
                        # regions = self.view.find_all(regexp)
                        # for region in  reversed(regions) :
                        #     self.view.insert(edit, region.a, "[")

                        # delete icons ![](http://www.site.com/Shared/ckeditor/plugins/SgFile/images/docx.png
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

            else:
                self.view.run_command('paste')

        elif IsClipboardFormatAvailable(CF_DIB):

            # calculate imagehash = md5(imgfile in clipboard)
            OpenClipboard(0)
            ClipboardHandle = GetClipboardData(CF_DIB)
            clipboard = ctypes.c_char_p(ClipboardHandle).value
            # hasher = hashlib.md5()
            # hasher.update(clipboard)
            # imagehash=hasher.hexdigest()
            imagehash = crc32(clipboard)
            print(imagehash)
            CloseClipboard()

            # relative file path
            rel_filename = os.path.join(
                "%s/%d.png" % (self.image_dir_name if self.image_dir_name else fn_without_ext, imagehash))
            # absolute file path
            abs_filename = os.path.join(subdir_name, "%d.png" % (imagehash))
            # if os.path.exists(abs_filename):
            # os.remove(abs_filename)
            print("dir_name is: "+rel_filename + "\nfile name is: " + abs_filename)

            im = ImageGrab.grabclipboard()
            # PIL只能支持24bit的png，hypersnap默认保存的png文件是32bit，需要修改设定，否则PIL不能识别
            im.save(abs_filename, 'PNG')
            for pos in view.sel():
            # print("scope name: %r" % (view.scope_name(pos.begin())))
                if 'text.html.markdown' in view.scope_name(pos.begin()):
                    view.insert(edit, pos.begin(), "![](%s)" % rel_filename)
                else:
                    view.insert(edit, pos.begin(), "%s" % rel_filename)
                # only the first cursor add the path
            print('image saved')


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
            # self.view.replace(edit, region, '#' +
            # current_line_text[2:len(current_line_text)])
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
