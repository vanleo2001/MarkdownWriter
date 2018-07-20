import sublime
import sublime_plugin
import os
import sys
import re
import time
import urllib.request
import imghdr
from . import html2text
import win32clipboard
import win32con
from . import HtmlClipboard
from imp import reload
# import hashlib
from zlib import crc32

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
        if win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_HDROP):
            win32clipboard.OpenClipboard()
            files=win32clipboard.GetClipboardData(win32clipboard.CF_HDROP)
            win32clipboard.CloseClipboard()
            lenfile=len(files)
            print("lenfile", lenfile)
            filelist=""
            if lenfile>0:
                for i in range(0, lenfile):
                    fn=files[i]
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

        elif win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_TEXT):
            # win32clipboard.OpenClipboard()
            # clipboard = win32clipboard.GetClipboardData()
            # win32clipboard.CloseClipboard()

            if HtmlClipboard.HasHtml():
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

                        # delete icons ![](http://zd.sharegreat.cn/exy/Shared/ckeditor/plugins/SgFile/images/docx.png
                        regexp2 = "!\[.*?]\(.*/ckeditor/(.*?\))"
                        regions2 = self.view.find_all(regexp2)
                        for region in  reversed(regions2) :
                            self.view.erase(edit, region)

                        regexp3 = "\r"
                        regions3 = self.view.find_all(regexp3)
                        for region in  reversed(regions3) :
                            self.view.erase(edit, region)

            else:
                self.view.run_command('paste')

        elif win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_DIB):

            # calculate imagehash = md5(imgfile in clipboard)
            win32clipboard.OpenClipboard()
            clipboard = win32clipboard.GetClipboardData(win32clipboard.CF_DIB)
            # hasher = hashlib.md5()
            # hasher.update(clipboard)
            # imagehash=hasher.hexdigest()
            imagehash = crc32(clipboard)
            print(imagehash)
            win32clipboard.CloseClipboard()

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
                self.view.replace(edit, region, region_text[
                                  1:len(region_text) - 1])
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
