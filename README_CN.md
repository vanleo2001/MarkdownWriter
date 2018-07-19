## 介绍
**MarkdownWriter**是一个Sublime Text 3 (windows)的插件，开发目的是使得写markdown更简单。

![](demo1.gif)

## 插件功能
1. **智能粘贴**
<br>(1) 如果你需要从网页中复制内容并保存为markdown格式笔记，你可以在浏览器中先复制需要的内容，再在Sublime Text中按快捷键<kbd>Ctrl</kbd>+<kbd>Alt</kbd>+<kbd>V</kbd> （或者鼠标右键菜单`Paste html or image`）进行粘贴，文本将自动转换为Markdown格式后粘贴，如果粘贴的文本中包含图片，图片会自动下载并保存在该md文件下"media"文件夹中。
<br>(2) 你可以在本地磁盘中copy一个或多个图像文件，再在Sublime Text中按快捷键<kbd>Ctrl</kbd>+<kbd>Alt</kbd>+<kbd>V</kbd> （或者鼠标右键菜单`Paste html or image`）进行粘贴，图像文件将自动转换为Markdown格式的链接文本插入，图像文件会自动保存在该md文件下"media"文件夹中。
<br>(3) 你也可以打开一个图像文件后复制图像，再在Sublime Text中按快捷键<kbd>Ctrl</kbd>+<kbd>Alt</kbd>+<kbd>V</kbd> （或者鼠标右键菜单`Paste html or image`）进行粘贴，图像将自动转换为Markdown格式后插入，图像文件也会自动保存在该md文件下"media"文件夹中。

2. **直接显示图像**
借助插件[MarkdownInlineImages plugin](https://github.com/math2001/MarkdownInlineImages), 按快捷键<kbd>Alt</kbd>+<kbd>I</kbd>来直接显示/关闭图像.

3. **添加文字加黑** 选择一些文本，按快捷键<kbd>Ctrl</kbd>+<kbd>Alt</kbd>+<kbd>B</kbd>使得加黑。

4. **添加文字斜体** 选择一些文本，按快捷键<kbd>Ctrl</kbd>+<kbd>Alt</kbd>+<kbd>I</kbd>使得斜体.

5. **添加二级标题** 光标定位到要加“标题格式”的行，按快捷键<kbd>Ctrl</kbd>+<kbd>Alt</kbd>+<kbd>2</kbd>添加/去除Headline2格式。

6. **添加三级标题** 光标定位到要加“标题格式”的行，按快捷键<kbd>Ctrl</kbd>+<kbd>Alt</kbd>+<kbd>3</kbd>添加/去除Headline3格式。

7. **添加四级标题** 光标定位到要加“标题格式”的行，按快捷键<kbd>Ctrl</kbd>+<kbd>Alt</kbd>+<kbd>4</kbd>添加/去除Headline4格式。

8. **智能列表** 进行列表编辑时， 按下回车键<kbd>Shift</kbd>+<kbd>Alt</kbd>+<kbd>Enter</kbd>后会自动插入有序列表的编号2. 3. 4. ...


## 安装
1. 手动安装: 下载并解压本插件，复制到"Sublime Text 3\Data\Packages\"下， 再用记事本打开"Sublime Text 3\Data\Packages\User\Package Control.sublime-settings"文件添加如下语句
```
"installed_packages":
    [
        "MarkdownWriter"
    ]
```


## Tips:
1. 为了正确使用本插件和MarkdownInlineImages插件, 需要设置markdown的syntax语法文件为"Markdown GFM"，我在插件包中提供了该文件；插件[Markdown​Editing](https://packagecontrol.io/packages/MarkdownEditing)也提供了相同的语法文件。Markdown syntax设置见下图：
![](demo2.png)

2. 我使用的是Sublime Text 3 32位版本, 所以本插件需要的library `Pillow`也是32位版本。如果你使用64位版本的Sublime Text 3，你需要将插件包中lib文件夹下的["PIL_x64.zip"](lib/PIL_x64.zip)解压，并覆盖32位版本的"PIL"文件夹。

3. 为了使用sublime text 3的直接显示图像功能，Sublime Text 3最低需要build 3118版本。