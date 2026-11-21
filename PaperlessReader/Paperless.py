#!/usr/bin/env python3

VERSION = "0.4.1"
ENAME = "Paperless"
ESITE = "https://github.com/frank038/Paperless"

import sys,os
import gi
gi.require_version("Gtk","4.0")
gi.require_version("Adw","1")
gi.require_version('Gdk', '4.0')
gi.require_version("GtkSource", "5")
from gi.repository import Gtk,Gdk,GLib,Gio,Adw,GObject,GtkSource,GdkPixbuf,Pango
import json
import posixpath
import urllib.parse
import zipfile
from html.parser import HTMLParser, unescape
import xml.etree.ElementTree as ET
import re
CLEANER = re.compile('<.*?>')

_app = None
self_main = None
_curr_dir = os.getcwd()
_HOME = os.path.expanduser("~")
icon_theme = Gtk.IconTheme.get_for_display(Gdk.Display.get_default())


# the directory settings and options
if not os.access(_curr_dir, os.W_OK):
    HOME_CONFIG = os.path.join(_HOME,".config","PrimsDM4")
    try:
        if not os.path.exists(HOME_CONFIG):
            os.mkdir(HOME_CONFIG, mode=0o770)
    except:
        HOME_CONFIG = _curr_dir
    if HOME_CONFIG != _curr_dir:
        try:
            shutil.copytree("/usr/share/PaperlessReader/configs", os.path.join(HOME_CONFIG, "configs"))
            shutil.copytree("/usr/share/PaperlessReader/icons", os.path.join(HOME_CONFIG, "icons"))
            shutil.copytree("/usr/share/PaperlessReader/langs", os.path.join(HOME_CONFIG, "langs"))
        except Exception as E:
            HOME_CONFIG = _curr_dir
else:
    HOME_CONFIG = _curr_dir

sys.path.append(os.path.join(HOME_CONFIG, "langs"))
_lang = __import__("en")

config_file = os.path.join(HOME_CONFIG, "configs/config.json")
config_conf_start = { 
"wwidth": 1200, 
"wheight": 800,
"foreground": "rgb(0,0,0)",
"background": "rgb(255,216,196)",
"fontfamily": "Sans",
"textsize": 12
}

if not os.path.exists(config_file):
    try:
        _data_json = config_conf_start
        _ff =  open(config_file, "w")
        json.dump(_data_json, _ff, indent = 4)
        _ff.close()
        config_conf = config_conf_start
    except:
        sys.exit()
else:
    try:
        _ff = open(config_file, "r")
        config_conf = json.load(_ff)
        _ff.close()
    except:
        sys.exit()

######### CONFIGURATION
WWIDTH = config_conf["wwidth"] # this program width
WHEIGHT = config_conf["wheight"] # this program height
FOREGROUND = config_conf["foreground"] # the font color
BACKGROUND = config_conf["background"] # the paper color
FONTFAMILY = config_conf["fontfamily"] # the font type
FONTSIZE = config_conf["textsize"] # the text size
######### 
IMAGEPAD = 100 # the width of this program less that number 

MENU_XML="""
<?xml version="1.0" encoding="UTF-8"?>
<interface>
  <menu id="app-menu">
    <section>
      <item>
        <attribute name="action">win.open</attribute>
        <attribute name="label" translatable="yes">{}</attribute>
      </item>
      <item>
        <attribute name="action">win.info</attribute>
        <attribute name="label" translatable="yes">{}</attribute>
      </item>
      <item>
        <attribute name="action">win.settings</attribute>
        <attribute name="label" translatable="yes">{}</attribute>
      </item>
      <item>
        <attribute name="action">win.about</attribute>
        <attribute name="label" translatable="yes">{}</attribute>
      </item>
      <item>
        <attribute name="action">win.quit</attribute>
        <attribute name="label" translatable="yes">{}</attribute>
        <attribute name="accel">&lt;Primary&gt;Q</attribute>
    </item>
    </section>
  </menu>
</interface>
""".format(_lang.OPEN, _lang.INFO, _lang.SETTINGS, _lang.ABOUT, _lang.QUIT)

NARROW = "max-width: {}sp".format(WWIDTH)

# book data
_title = ""
_creator = ""
_date = ""
_language = ""
_subject = ""
_coverage = ""
_rights = ""
_publisher = ""
_description = ""

manifest_list = []
pages_list = []
class EpubDataParser(HTMLParser):
    
    def handle_starttag(self, tag, attrs):
        if tag == "item":
            manifest_list.append(attrs)
        # el
        if tag == "dc:title":
            global _title
            _title = "dc:title"
        elif tag == "dc:creator":
            global _creator
            _creator = "dc:creator"
        elif tag == "dc:date":
            global _date
            _date = "dc:date"
        elif tag == "dc:language":
            global _language
            _language = "dc:language"
        elif tag == "dc:subject":
            global _subject
            _subject = "dc:subject"
        elif tag == "dc:coverage":
            global _coverage
            _coverage = "dc:coverage"
        elif tag == "dc:rights":
            global _rights
            _rights = "dc:rights"
        elif tag == "dc:publisher":
            global _publisher
            _publisher = "dc:publisher"
        elif tag == "dc:description":
            global _description
            _description = "dc:description"
        #
        if tag == "itemref":
            pages_list.append(attrs)

    def handle_endtag(self, tag):
        pass

    def handle_data(self, data):
        global _title
        global _creator
        global _date
        global _language
        global _subject
        global _coverage
        global _rights
        global _publisher
        global _description
        if _title == "dc:title":
            _title = data
        if _creator == "dc:creator":
            _creator = data
        if _date == "dc:date":
            _date = data
        if _language == "dc:language":
            _language = data
        if _subject == "dc:subject":
            _subject = data
        if _coverage == "dc:coverage":
            _coverage = data
        if _rights == "dc:rights":
            _rights = data
        if _publisher == "dc:publisher":
            _publisher = data
        if _description == "dc:description":
            _description = data

class EpubFormattedImageParser(HTMLParser):

    def __init__(self, buffer, zip_file, current_html_path, max_width=WWIDTH-IMAGEPAD):
        super().__init__()
        self.buffer = buffer
        self.zip_file = zip_file
        self.base_dir = posixpath.dirname(current_html_path)
        self.max_width = max_width
        self.ignore_content = False
        self.active_tags = []
        self.namelist = set(zip_file.namelist())
        self.lower_map = {name.lower(): name for name in self.namelist}

    def handle_starttag(self, tag, attrs):
        tag = tag.split(":")[-1].lower()
        attrs_dict = dict(attrs)
        
        if tag in ("head", "style", "script", "title"):
            self.ignore_content = True
            return
        # titles (h1..h6)
        if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self._insert_newline_if_needed()
            self.active_tags.append(tag)
        # inline titles
        elif tag in ("b", "strong"):
            self.active_tags.append("bold")
        elif tag in ("i", "em"):
            self.active_tags.append("italic")
        elif tag == "u":
            self.active_tags.append("underline")
        elif tag in ("s", "strike", "del"):
            self.active_tags.append("strikethrough")
        elif tag in ("code", "pre", "tt"):
            self.active_tags.append("monospace")
        # blocks and quotes
        elif tag == "blockquote":
            self._insert_newline_if_needed()
            self.active_tags.append("quote")
        elif tag == "li":
            self._insert_newline_if_needed()
            self._insert_text("• ")
        elif tag in ("p", "div"):
            self._insert_newline_if_needed()
        elif tag == "br":
            self._insert_text("\n")
        # images
        if tag in ("img", "image"):
            src = (
                attrs_dict.get("src")
                or attrs_dict.get("href")
                or attrs_dict.get("xlink:href")
            )
            if src:
                self._insert_image(src)
    
    def handle_endtag(self, tag):
        tag = tag.split(":")[-1].lower()
        
        if tag in ("head", "style", "script", "title"):
            self.ignore_content = False
        elif tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self._remove_tag(tag)
            self._insert_text("\n\n")
        elif tag in ("b", "strong"):
            self._remove_tag("bold")
        elif tag in ("i", "em"):
            self._remove_tag("italic")
        elif tag == "u":
            self._remove_tag("underline")
        elif tag in ("s", "strike", "del"):
            self._remove_tag("strikethrough")
        elif tag in ("code", "pre", "tt"):
            self._remove_tag("monospace")
        elif tag == "blockquote":
            self._remove_tag("quote")
            self._insert_text("\n\n")
        elif tag in ("p", "div", "li"):
            self._insert_text("\n\n")

    def _remove_tag(self, tag_name):
        if tag_name in self.active_tags:
            idx = len(self.active_tags) - 1 - self.active_tags[::-1].index(tag_name)
            self.active_tags.pop(idx)

    def handle_data(self, data):
        if self.ignore_content:
            return
        clean = " ".join(data.split())
        if clean:
            end_iter = self.buffer.get_end_iter()
            if not end_iter.starts_line() and not clean.startswith(
                (".", ",", ";", ":", "!", "?", ")", "]")
            ):
                self._insert_text(" ")
            self._insert_text(clean)

    def _insert_newline_if_needed(self):
        end_iter = self.buffer.get_end_iter()
        if end_iter.get_offset() > 0 and not end_iter.starts_line():
            self._insert_text("\n")

    def _insert_text(self, text):
        end_iter = self.buffer.get_end_iter()
        if self.active_tags:
            # remove duplicates
            unique_tags = list(dict.fromkeys(self.active_tags))
            self.buffer.insert_with_tags_by_name(end_iter, text, *unique_tags)
        else:
            self.buffer.insert(end_iter, text)

    def _insert_image(self, src):
        clean_src = urllib.parse.unquote(src.split("#")[0])
        joined = (
            posixpath.join(self.base_dir, clean_src)
            if self.base_dir
            else clean_src
        )
        norm_path = posixpath.normpath(joined).lstrip("/")
        real_path = (
            norm_path
            if norm_path in self.namelist
            else self.lower_map.get(norm_path.lower())
        )
        if not real_path:
            return
        try:
            img_bytes = self.zip_file.read(real_path)
            stream = GdkPixbuf.PixbufLoader()
            stream.write(img_bytes)
            stream.close()
            pixbuf = stream.get_pixbuf()
            if pixbuf:
                w = pixbuf.get_width()
                h = pixbuf.get_height()
                # if w > self.max_width:
                new_h = int(h * (self.max_width / w))
                pixbuf = pixbuf.scale_simple(
                    self.max_width, new_h, GdkPixbuf.InterpType.BILINEAR
                )
                texture = Gdk.Texture.new_for_pixbuf(pixbuf)
                self._insert_newline_if_needed()
                # center the image using the tag center
                start_offset = self.buffer.get_end_iter().get_offset()
                self.buffer.insert_paintable(self.buffer.get_end_iter(), texture)
                start_iter = self.buffer.get_iter_at_offset(start_offset)
                end_iter = self.buffer.get_end_iter()
                self.buffer.apply_tag_by_name("center", start_iter, end_iter)
                self._insert_text("\n\n")
        except Exception as E:
            self._insert_text("\n{} {}\n".format(_lang.IMAGECANNOTLOAD, real_path))

class _DeHTMLParser(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
        self.__text = []

    def handle_data(self, data):
        text = data.strip()
        if len(text) > 0:
            text = re.sub('[ \t\r\n]+', ' ', text)
            self.__text.append(text + ' ')

    def handle_starttag(self, tag, attrs):
        if tag == 'p':
            self.__text.append('\n\n')
        elif tag == 'br':
            self.__text.append('\n')

    def handle_startendtag(self, tag, attrs):
        if tag == 'br':
            self.__text.append('\n\n')

    def text(self):
        return ''.join(self.__text).strip()


def buffer_styles(buffer):
    # GtkSource.Buffer styles
    buffer.create_tag("bold", weight=Pango.Weight.BOLD)
    buffer.create_tag("italic", style=Pango.Style.ITALIC)
    buffer.create_tag("underline", underline=Pango.Underline.SINGLE)
    buffer.create_tag("strikethrough", strikethrough=True)
    buffer.create_tag("monospace", family="Monospace", scale=0.95)
    buffer.create_tag("center", justification=Gtk.Justification.CENTER)

    # titles
    buffer.create_tag(
        "h1",
        weight=Pango.Weight.BOLD,
        scale=1.6,
        pixels_above_lines=20,
        pixels_below_lines=10,
    )
    buffer.create_tag(
        "h2",
        weight=Pango.Weight.BOLD,
        scale=1.4,
        pixels_above_lines=16,
        pixels_below_lines=8,
    )
    buffer.create_tag(
        "h3",
        weight=Pango.Weight.BOLD,
        scale=1.2,
        pixels_above_lines=12,
        pixels_below_lines=6,
    )
    for h_tag in ("h4", "h5", "h6"):
        buffer.create_tag(
            h_tag,
            weight=Pango.Weight.BOLD,
            scale=1.1,
            pixels_above_lines=8,
            pixels_below_lines=4,
        )

    # quotes
    buffer.create_tag(
        "quote",
        left_margin=32,
        right_margin=32,
        style=Pango.Style.ITALIC,
    )

    # end chapter separator
    buffer.create_tag(
        "chapter_sep",
        family="Monospace",
        scale=0.85,
        foreground="#888888",
        justification=Gtk.Justification.CENTER,
    )

CHAPTERS = []
_zipfile = None
def load_chapters(epub_path):
    global _zipfile
    global CHAPTERS
    CHAPTERS = []
    _zipfile = zipfile.ZipFile(epub_path, "r")
    # _chaptrs = sorted([
        # _f
        # for _f in _zipfile.namelist()
        # if _f.lower().endswith((".xhtml", ".html", ".htm"))
    # ])
    _chaptrs = [
        _f
        for _f in _zipfile.namelist()
        if _f.lower().endswith((".xhtml", ".html", ".htm"))
    ]
    #
    for _chap in _chaptrs:
        CHAPTERS.append(_chap)

def replace_text(aaa):
    _start = aaa.find("<!DOCTYPE")
    _end = aaa.find("]>", _start)
    # the block to identify and remove
    bbb = aaa[_start: _end+2]
    _list = []
    ret = bbb.find("<!ENTITY")
    if ret != -1:
        _list.append(ret)
        #
        while ret != -1:
            ret = bbb.find("<!ENTITY", _list[-1]+8)
            if ret != -1:
                _list.append(ret)
    #
    if _list == []:
        return aaa
    #
    entity_list = []
    for i,el in enumerate(_list[:]):
        if i == len(_list)-1:
            break
        _e = _list[i+1]+_start
        entity_list.append(aaa[ el+_start : _e ].rstrip("\n"))
    #
    entity_list.append(bbb[_list[-1]:].rstrip("\n"))
    if entity_list == []:
        return aaa
    _code_list = []
    for el in entity_list:
        _l = el.split(" ")
        _c = _l[1]
        _d = _l[2].split(";")[0][1:]
        _code_list.append([_c,_d])
    #
    ccc = aaa.replace(bbb, "")
    for el in _code_list:
        ccc = ccc.replace("&{};".format(el[0]), unescape(el[1]))
    #
    return ccc


class MainWindow(Adw.ApplicationWindow):
    def __init__(self, _files, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_default_size(WWIDTH, WHEIGHT)
        self.app_ = self.get_application()
        self.set_title(ENAME)
        self.set_icon_name("com.Paperless.epubreader")
        if _files == None:
            sys.exit(-1)
        self.epub_path = _files.get_path()
        #
        global self_main
        self_main = self
        self.connect("close-request", self.on_this_close)
        try:
            self.connect("force-close", self.on_this_close)
        except:
            pass
        self.connect("destroy", self.on_this_close)
        self.connect("show", self.on_show)
        #
        self.provider = Gtk.CssProvider()
        self.set_custom_settings(FOREGROUND, BACKGROUND, FONTSIZE, FONTFAMILY)
        #
        self.mainvbox = Gtk.Box.new( Gtk.Orientation.VERTICAL,6)
        #
        self.headerbar = Adw.HeaderBar.new() 
        # this is the page
        self.page_box = Gtk.Box.new(Gtk.Orientation.HORIZONTAL, spacing=0)
        self.page_box.set_hexpand(True)
        self.page_box.set_vexpand(True)
        self.mainvbox.append(self.page_box)
        #
        self.scrolled = Gtk.ScrolledWindow()
        self.page_box.append(self.scrolled)
        #
        quit_action = Gio.SimpleAction.new("quit", None) 
        quit_action.connect("activate", self.on_quit_action_actived)
        self.add_action(quit_action)
        #
        about_action = Gio.SimpleAction.new("about", None)
        about_action.connect("activate", self.on_about_action_actived)
        self.add_action(about_action)
        #
        settings_action = Gio.SimpleAction.new("settings", None) 
        settings_action.connect("activate", self.on_settings_action_actived)
        self.add_action(settings_action)
        #
        info_action = Gio.SimpleAction.new("info", None)
        info_action.connect("activate", self.on_info_action_actived)
        self.add_action(info_action)
        #
        new_action = Gio.SimpleAction.new("open", None)
        new_action.connect("activate", self.on_new_file)
        self.add_action(new_action)
        #
        self.menu_button = Gtk.MenuButton.new()
        self.headerbar.pack_end(self.menu_button)
        menu = Gtk.Builder.new_from_string(MENU_XML, -1).get_object("app-menu")
        self.menu_button.set_icon_name("open-menu-symbolic")
        self.menu_button.set_menu_model(menu)
        #
        self.stack = Gtk.Stack(transition_type=Gtk.StackTransitionType.CROSSFADE)
        self.sidebar_list = Gtk.ListBox(selection_mode=Gtk.SelectionMode.SINGLE)
        self.sidebar_list.add_css_class("navigation-sidebar")
        self.sidebar_scroll = Gtk.ScrolledWindow.new()
        self.sidebar_scroll.set_child(self.sidebar_list)
        #
        self.stack.add_named(self.mainvbox, "title")
        #
        self.split = Adw.OverlaySplitView(sidebar=self._sidebar(self.sidebar_scroll),
                                          content=self._content())
        self.set_content(self.split)
        #
        narrow = Adw.Breakpoint.new(Adw.BreakpointCondition.parse(NARROW))
        narrow.add_setter(self.split, "collapsed", True)
        narrow.add_setter(self.show_sidebar_button, "visible", True)
        self.add_breakpoint(narrow)
        ######
        GtkSource.init()
        self.buffer = GtkSource.Buffer()
        buffer_styles(self.buffer)
        #
        self.current_page = -1
        self._opf_file = None
        self.VERSION = 0
        self.TOC_NAVIGATION = []
        #
        self.source_view = GtkSource.View.new_with_buffer(self.buffer)
        self.source_view.set_name("textview1")
        self.source_view.set_hexpand(True)
        self.source_view.set_vexpand(True)
        self.source_view.set_editable(False)
        self.source_view.set_cursor_visible(False)
        self.source_view.set_wrap_mode(Gtk.WrapMode.WORD)
        self.source_view.set_top_margin(20)
        self.source_view.set_bottom_margin(20)
        self.source_view.set_left_margin(32)
        self.source_view.set_right_margin(32)
        # self.source_view.set_pixels_above_lines(3)
        # self.source_view.set_pixels_below_lines(3)
        self.source_view.set_justification(Gtk.Justification.FILL)
        self.scrolled.set_child(self.source_view)
        #
        # the left panel is now hidden
        self.show_sidebar_button.bind_property(
            "active", self.split, "show-sidebar",
            GObject.BindingFlags.BIDIRECTIONAL | GObject.BindingFlags.SYNC_CREATE)
        # the epub infos
        self._info_data = ""
        # process and load the epub file
        self.on_start(self.epub_path)
        #
        self.wheel_ctrl = Gtk.EventControllerScroll.new(Gtk.EventControllerScrollFlags.BOTH_AXES)
        self.wheel_ctrl.connect("scroll", self.on_wheel_scroll)
        self.source_view.add_controller(self.wheel_ctrl)
        #
        self.key_ctrl = Gtk.EventControllerKey()
        self.key_ctrl.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        self.key_ctrl.connect("key-pressed", self.on_key_pressed)
        self.add_controller(self.key_ctrl)
    
    def on_new_file(self, action, param=None):
        _fd = Gtk.FileDialog.new()
        _fd.set_modal(True)
        _fd.set_initial_folder(Gio.File.new_for_path(_HOME))
        def open_callback(source_object, res, data):
            try:
                l_gfile = _fd.open_text_file_finish(res)
                _file = l_gfile[0].get_path()
                self.on_start(_file)
            except GLib.GError as e:
                return
        try:
            _fd.open_text_file(self, None, open_callback, None)
        except Exception as E:
            AlDial(self_main, str(E))
    
    # process and load the epub file
    def on_start(self, file_path):
        global _title
        global _creator
        global _date
        global _language
        global _subject
        global _coverage
        global _rights
        global _publisher
        global _description
        global manifest_list
        global pages_list
        global CHAPTERS
        global _zipfile
        _title = ""
        _creator = ""
        _date = ""
        _language = ""
        _subject = ""
        _coverage = ""
        _rights = ""
        _publisher = ""
        _description = ""
        manifest_list = []
        pages_list = []
        CHAPTERS = []
        _zipfile = None
        self.buffer.set_text("", -1)
        # the real pages to read - filename with path
        self._list_pages = []
        if os.path.exists(file_path):
            try:
                load_chapters(file_path)
                # find the opf file inside the container.xml file
                opf_tmp = None
                opf_file = None
                for el in _zipfile.filelist:
                    if os.path.basename(el.filename) == "container.xml":
                        opf_tmp = _zipfile.read(el.filename).decode()
                        break
                if opf_tmp != None:
                    _aa = opf_tmp.find('full-path="')
                    if _aa != -1:
                        _bb = opf_tmp.find('"', _aa+11)
                        opf_file = opf_tmp[_aa+11:_bb]
                if opf_file != None:
                    for el in _zipfile.filelist:
                        if el.filename == opf_file:
                            self._opf_file = _zipfile.read(el.filename).decode()
                            break
                # or find the first
                if self._opf_file == None:
                    for el in _zipfile.filelist:
                        if el.filename.endswith(".opf"):
                            self._opf_file = _zipfile.read(el.filename).decode()
                            break
            except Exception as e:
                self.buffer.set_text("{} {}".format(_lang.ERRORLOADEPUB, e))
                return
        else:
            self.buffer.set_text("{}\n{}".format( _lang.FILENOTFOUND, self.epub_path))
            return
        #
        if self._opf_file:
            # find the epub version
            _aa = self._opf_file.find("<package")
            if _aa != -1:
                _bb = self._opf_file.find("version", _aa+1)
                if _bb != -1:
                    _cc = self._opf_file.find('"', _bb+1)
                    if _cc != -1:
                        _dd = self._opf_file.find('"', _cc+1)
                        if _dd != -1:
                            self.VERSION = self._opf_file[_cc+1:_dd]
        #
        if self.VERSION == 0 or self.VERSION[0] == "2" or self.VERSION[0] == "1":
            manifest_list = [] # reset
            pages_list = [] # reset
            # find how mani opf file there are in the epub file: only one is allowed
            n_opf = 0
            for el in _zipfile.filelist:
                if el.filename.endswith(".opf"):
                    n_opf += 1
            #
            if n_opf == 1:
                parser = EpubDataParser()
                parser.feed(self._opf_file)
                parser.close()
                #
                # the cover
                self._COV = None
                # the navigation page
                self._NAV = None
                # the toc
                self._TOC = None
                #
                # find cover - navigation - TOC
                self.find_cov_nav_toc(self._list_pages)
                #
                TOC_DATA = ""
                for el in _zipfile.filelist:
                    if el.filename.endswith(".ncx"):
                        self._TOC = el.filename
                        TOC_DATA = _zipfile.read(el.filename).decode()
                        break
                #
                if TOC_DATA:
                    self.find_toc_data(TOC_DATA)
                parser.close()
                # 
                # create the index
                self.sidebar_list.remove_all()
                #
                if self._list_pages:
                    for i,_d in enumerate(self._list_pages):
                        _navlabel = _d
                        _tmp = _d
                        if self.TOC_NAVIGATION:
                            for ell in self.TOC_NAVIGATION:
                                if ell[3] == _navlabel:
                                    _navlabel = ell[2]
                                    break
                        #
                        _action = Adw.ActionRow(title=_navlabel, icon_name="terminal")
                        _action.set_activatable(True)
                        _action.set_selectable(True)
                        self.sidebar_list.append(_action)
                        #
                        for ii,_c in enumerate(CHAPTERS):
                            if os.path.basename(_c) == os.path.basename(_tmp):
                                _action._filenav = _tmp
                                _action._file = _c
                                _action._real_idx = i
                                _action._idx = ii
                                _action.connect("activated", self.on_action_activated2)
                                break
            if n_opf > 1:
                # create the index
                self.sidebar_list.remove_all()
                #
                for i,eel in enumerate(CHAPTERS):
                    _navlabel = os.path.basename(eel)
                    _action = Adw.ActionRow(title=_navlabel, icon_name="terminal")
                    _action.set_activatable(True)
                    _action.set_selectable(True)
                    self.sidebar_list.append(_action)
                    #
                    _action._filenav = _navlabel
                    _action._file = eel
                    _action._real_idx = i
                    _action._idx = i
                    _action.connect("activated", self.on_action_activated2)
        elif self.VERSION[0] == "3":
            manifest_list = [] # reset
            pages_list = [] # reset
            parser = EpubDataParser()
            parser.feed(self._opf_file)
            #
            # the navigation page is in MANIFEST with properties nav
            _file_nav = ""
            def found_file_nav():
                for el in manifest_list:
                    for ell in el:
                        if ell[0] == "href":
                            _file_nav = ell[1]
                            for elll in el:
                                if elll[0] == "properties" and elll[1] == "nav":
                                    return _file_nav
            _file_nav = found_file_nav()
            # file cover
            _file_cover = ""
            def found_file_cov():
                for el in manifest_list:
                    for ell in el:
                        if ell[0] == "href":
                            _file_cover = ell[1]
                            for elll in el:
                                if elll[0] == "properties" and elll[1] == "cover-image":
                                    return _file_cover
            _file_cover = found_file_cov()
            #
            if _file_nav:
                # create the index
                self.sidebar_list.remove_all()
                # navigation file content
                _NFC = None
                _COMMON_PATH = "" # where the xhtml files are - they must be inside OEBPS
                for el in _zipfile.filelist:
                    if os.path.basename(el.filename) == os.path.basename(_file_nav):
                        _NFC = _zipfile.read(el.filename).decode()
                        _COMMON_PATH = os.path.dirname(el.filename)
                        break
                LIST_TOC = []
                if _NFC:
                    # find the file xhtml name
                    _aa = _NFC.find("href")
                    while _aa != -1:
                        _bb = _NFC.find('"',_aa+1)
                        if _bb != -1:
                            _cc = _NFC.find('">',_bb+1)
                            # find the TOC name
                            if _cc != -1:
                                _dd = _NFC.find("</a>", _cc+1)
                                if _dd != -1:
                                    _href = _NFC[_bb+1:_cc]
                                    _name = _NFC[_cc+2:_dd]
                                    try:
                                        parser = _DeHTMLParser()
                                        parser.feed(_name)
                                        _name = parser.text()
                                        parser.close()
                                    except:
                                        _name = _NFC[_cc+2:_dd]
                                    #
                                    LIST_TOC.append([_href, _name])
                        #
                        _aa = _NFC.find("href", _aa+4)
                #
                if LIST_TOC:
                    for i,el in enumerate(pages_list):
                        _ref = el[0][1] # page name code
                        for ell in manifest_list:
                            _page_file_name = ""
                            _page_path = ""
                            for elll in ell:
                                if elll[1] == _ref: # page name code
                                    for eel in ell:
                                        if eel[0] == "href":
                                            _page_path = eel[1]
                                            _page_file_name = eel[1] # os.path.basename(eel[1])
                                            break
                                            break
                                            break
                            #
                            if _page_file_name:
                                toc_entry = "Page"
                                # toc_entry = _page_file_name
                                for el in LIST_TOC:
                                    if os.path.basename(el[0]) == os.path.basename(_page_file_name):
                                        toc_entry = el[1]
                                        break
                                _action = Adw.ActionRow.new()
                                _action.set_use_markup(False)
                                # _action.set_title(toc_entry)
                                _action.set_title(re.sub(CLEANER, '', toc_entry))
                                # ''.join(xml.etree.ElementTree.fromstring(text).itertext())
                                _action.set_activatable(True)
                                _action.set_selectable(True)
                                self.sidebar_list.append(_action)
                                _action._filenav = _COMMON_PATH+"/"+_page_file_name
                                _action._file = os.path.basename(_page_file_name) # filename only
                                _action._real_idx = i
                                _action._idx = i
                                _action.connect("activated", self.on_action_activated3)
        ################
        # the epub infos
        try:
            parser = _DeHTMLParser()
            parser.feed(_description)
            _description = parser.text()
            parser.close()
        except:
            pass
        #
        if _title:
            self.set_title(_title)
        else:
            self.set_title(os.path.basename(file_path))
        ##### load the first page
        row = self.sidebar_list.get_row_at_index(0)
        if row:
            row.emit("activated")
            self.sidebar_list.select_row(row)
    
    # load the page number _page
    def load_epub_page3(self, buffer, _page, filenav):
        if _zipfile != None:
            buffer.set_text("", -1)
            self.current_page = _page
            _f = _zipfile
            _chaptrs = sorted([
                f
                for f in _f.namelist()
                if f.lower().endswith((".xhtml", ".html", ".htm"))
            ])
            #
            _chap = None
            for _c in _chaptrs:
                if os.path.basename(_c) == os.path.basename(filenav):
                    _chap = _c
                    break
            if _chap:
                _html = _f.read(_chap).decode(
                    "utf-8", errors="ignore"
                )
                _html = replace_text(_html)
                buffer.insert_with_tags_by_name(
                    buffer.get_end_iter(), "", "chapter_sep"
                )
                parser = EpubFormattedImageParser(buffer, _f, _chap)
                parser.feed(_html)
    
    def on_action_activated3(self, row):
        idx = row._idx
        real_idx = row._real_idx
        chapter = row._file
        filenav = row._filenav
        if idx == self.current_page:
            return
        self.current_page = idx
        row._idx = idx
        self.load_epub_page3(self.buffer, self.current_page, filenav)
        _adj = self.scrolled.get_vadjustment()
        self.scrolled.set_vadjustment(_adj.set_value(0))
    
    # load the page number _page
    def load_epub_page2(self, buffer, _page):
        if _zipfile != None:
            buffer.set_text("", -1)
            self.current_page = _page
            _f = _zipfile
            # _chaptrs = sorted([
                # f
                # for f in _f.namelist()
                # if f.lower().endswith((".xhtml", ".html", ".htm"))
            # ])
            #
            # for _chap in _chaptrs:
            _chap = CHAPTERS[_page]
            _html = _f.read(_chap).decode(
                "utf-8", errors="ignore"
            )
            _html = replace_text(_html)
            buffer.insert_with_tags_by_name(
                buffer.get_end_iter(), "", "chapter_sep"
            )
            parser = EpubFormattedImageParser(buffer, _f, _chap)
            parser.feed(_html)
    
    def on_action_activated2(self, row):
        idx = row._idx
        real_idx = row._real_idx
        chapter = row._file
        #
        if idx == self.current_page:
            return
        self.current_page = idx
        row._idx = idx
        self.load_epub_page2(self.buffer, self.current_page)
        _adj = self.scrolled.get_vadjustment()
        self.scrolled.set_vadjustment(_adj.set_value(0))
    
    def scroll_next(self):
        _adj = self.scrolled.get_vadjustment()
        if _adj.get_value() + _adj.get_page_size() == _adj.get_upper():
            selected_row = self.sidebar_list.get_selected_row()
            if selected_row == None:
                selected_row = self.sidebar_list.get_first_child()
            row = selected_row.get_next_sibling()
            if row:
                row.emit("activated")
                self.sidebar_list.select_row(row)
        
    def scroll_prev(self):
        _adj = self.scrolled.get_vadjustment()
        if _adj.get_value() == _adj.get_lower():
            selected_row = self.sidebar_list.get_selected_row()
            if selected_row:
                curr_idx = selected_row.get_index()
                if curr_idx > 0:
                    _row = self.sidebar_list.get_row_at_index(curr_idx-1)
                    _row.emit("activated")
                    self.sidebar_list.select_row(_row)
                    self.scrolled.set_vadjustment(_adj.set_value(_adj.get_upper()-_adj.get_page_size()))
    
    def on_wheel_scroll(self, ctrl, dx, dy):
        if dy == -1.0:
            self.scroll_prev()
        elif dy == 1.0:
            self.scroll_next()
    
    def on_key_pressed(self, ctrl, keyval, keycode, state):
        if keyval == Gdk.KEY_Page_Down:
            if not self.source_view.has_focus():
                self.source_view.grab_focus()
            self.scroll_next()
        elif keyval == Gdk.KEY_Page_Up:
            if not self.source_view.has_focus():
                self.source_view.grab_focus()
            self.scroll_prev()
    
    def on_show(self, _w):
        _adj = self.scrolled.get_vadjustment()
        self.scrolled.set_vadjustment(_adj.set_value(0))
    
    # find cover - navigation - TOC
    def find_cov_nav_toc(self, _list_pages):
        for el in manifest_list:
            if self._NAV == None or not isinstance(self._NAV,str):
                for ell in el:
                    if ell[0] == 'properties':
                        if ell[1] == 'nav':
                            self._NAV = 1
            if self._NAV == 1:
                for ell in el:
                    if ell[0] == 'href':
                        self._NAV = os.path.basename(ell[1])
            #
            if self._COV == None or not isinstance(self._COV,str):
                for ell in el:
                    if ell[0] == 'properties':
                        if ell[1] == 'cover-image':
                            self._COV = 1
            if self._COV == 1:
                for ell in el:
                    if ell[0] == 'href':
                        self._COV = os.path.basename(ell[1])
            #
            if self._TOC == None or not isinstance(self._COV,str):
                for ell in el:
                    if ell[1] == 'ncx':
                        self._TOC = 1
            if self._TOC == 1:
                for ell in el:
                    if ell[0] == 'href':
                        self._TOC = ell[1]
        #
        # the real pages to read - filename with path
        for el in pages_list:
            # the page identifier found in the manifest e.g. titlepage
            _p = el[0][1]
            for ell in manifest_list:
                if ('id', _p) in ell:
                    for elll in ell:
                        if elll[0] == 'href':
                            _p_name = elll[1]
                            if _p_name[0:2] == "./":
                                _p_name = _p_name[2:]
                            _list_pages.append(urllib.parse.unquote(_p_name))
    
    def find_toc_data(self, TOC_DATA):
        try:
            start_pos = 0
            while start_pos != -1:
                _ID = ""
                _PLAYORDER = ""
                _NAVLABEL = ""
                _SRC = ""
                aa = -1
                bb = -1
                cc = -1
                dd = -1
                ee = -1
                ff = -1
                gg = -1
                hh = -1
                ### 1. navPoint
                start_pos = TOC_DATA.find("<navPoint", start_pos)
                end_pos = TOC_DATA.find("</navPoint>", start_pos)
                NAV_DATA = TOC_DATA[start_pos:end_pos+1]
                #
                # a. id
                aa = NAV_DATA.find('id', 0)
                if aa != -1:
                    bb1 = NAV_DATA.find('"',aa)
                    bb = NAV_DATA.find('"',bb1+1)
                    _ID = NAV_DATA[bb1+1:bb]
                if _ID == "":
                    continue
                # b. playOrder
                cc = NAV_DATA.find('playOrder', 0)
                if cc != -1:
                    dd1 =  NAV_DATA.find('"',cc)
                    dd = NAV_DATA.find('"',dd1+1)
                    _PLAYORDER = NAV_DATA[dd1+1:dd]
                # c. navLabel
                ee = NAV_DATA.find('<navLabel>', 0)
                if ee != -1:
                    ff = NAV_DATA.find('</navLabel>', ee)
                    _NAVLABEL = NAV_DATA[ee+10:ff].strip().replace("<text>","").replace("</text>","")
                # d. content src - the file xhtml/html
                gg = NAV_DATA.find('<content', 0)
                if gg != -1:
                    hh1 = NAV_DATA.find('"', gg)
                    hh = NAV_DATA.find("/>", hh1)
                    _SRC = NAV_DATA[hh1+1:hh-1].rstrip(" ")
                    if _SRC[-1] == '"':
                        _SRC = _SRC[0:-1]
                #
                self.TOC_NAVIGATION.append([_ID,_PLAYORDER,_NAVLABEL,_SRC])
                #
                if start_pos == -1:
                    break
                start_pos = end_pos
        except:
            self.TOC_NAVIGATION = []
        
    def set_custom_settings(self, foreground, background, fontsize, fontfamily):
        css = "#textview1 {"+"color: {};".format(foreground)+"background-color: {};".format(background)+"font-size: {}pt;".format(fontsize)+"font-family: {};".format(FONTFAMILY)+"}"
        self.provider.load_from_string(css)
        Gtk.StyleContext.add_provider_for_display(
            self.get_display(), self.provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )
    
    def _sidebar(self, listbox):
        toolbar = Adw.ToolbarView()
        topbar = Adw.HeaderBar(title_widget=Gtk.Label(label=_lang.INDEX), show_title=True, show_end_title_buttons=False)
        toolbar.add_top_bar(topbar)
        toolbar.set_content(listbox)
        return toolbar
    
    def _content(self):
        self.show_sidebar_button = Gtk.ToggleButton(icon_name="sidebar-show-symbolic",
                                                    visible=False)
        self.show_sidebar_button.set_tooltip_text("Show sidebar")
        self.headerbar.pack_start(self.show_sidebar_button)
        toolbar = Adw.ToolbarView()
        toolbar.add_top_bar(self.headerbar)
        toolbar.set_content(self.stack)
        return toolbar
    
    def on_info_action_actived(self, action, param=None):
        _infodlg = Adw.Dialog.new()
        _ibox = Gtk.Box.new(Gtk.Orientation.VERTICAL,10)
        _ibox.set_hexpand(True)
        _ibox.set_vexpand(True)
        _infodlg.set_child(_ibox)
        _ibox.set_margin_top(10)
        _ibox.set_margin_start(10)
        _ibox.set_margin_end(10)
        _ibox.set_margin_bottom(10)
        _scroll = Gtk.ScrolledWindow.new()
        _scroll.set_hexpand(True)
        _scroll.set_vexpand(True)
        _ibox.append(_scroll)
        _ilbl = Gtk.Label.new()
        _scroll.set_child(_ilbl)
        _ilbl.set_wrap(True)
        _ilbl.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
        _itext = "{} {}\n{} {}\n{} {}\n{} {}\n{} {}\n{} {}\n{} {}\n{} {}\n{} {}".format(_lang.TITLE, _title, _lang.CREATOR, _creator, _lang.DATE, _date, _lang.LANGUAGE, _language, _lang.SUBJECT, _subject, _lang.COVERAGE, _coverage, _lang.RIGHTS, _rights, _lang.PUBLISHER, _publisher, _lang.DESCRIPTION, _description)
        _ilbl.set_label(_itext)
        _ibtn = Gtk.Button(label=_lang.CLOSE)
        def on_idlg_close(_w):
            _infodlg.close()
        _ibtn.connect("clicked", on_idlg_close)
        _ibox.append(_ibtn)
        _infodlg.set_content_width(WWIDTH-200)
        _infodlg.set_content_height(WHEIGHT-200)
        _infodlg.present(self)
    
    def on_settings_action_actived(self, action, param=None):
        WinSettings(self)
    
    def on_about_action_actived(self, action, param=None):
        _aboutdial = Adw.AboutDialog.new()
        _aboutdial.set_presentation_mode(Adw.DialogPresentationMode.FLOATING)#.BOTTOM_SHEET)#.FLOATING)
        _aboutdial.set_application_icon("com.Paperless.epubreader")
        _aboutdial.set_developers(["Philip J. Fry"])
        _aboutdial.set_comments("Made for me 🙂")
        _aboutdial.set_version(VERSION)
        _aboutdial.set_website(ESITE)
        _aboutdial.set_license_type(Gtk.License.GPL_3_0_ONLY)
        _aboutdial.present(self)
    
    def on_quit_action_actived(self, action, param=None):
        global _zipfile
        if _zipfile:
            _zipfile.close()
        self.app_.quit()
    
    def on_this_close(self, _w):
        global WWIDTH
        global WHEIGHT
        _WWIDTH = self.get_width()
        _WHEIGHT = self.get_height()
        if _WWIDTH != WWIDTH or _WHEIGHT != WHEIGHT:
            WWIDTH = _WWIDTH
            config_conf["wwidth"] = WWIDTH
            WHEIGHT = _WHEIGHT
            config_conf["wheight"] = WHEIGHT
            try:
                _ff =  open(os.path.join(HOME_CONFIG,"configs/config.json"), "w")
                json.dump(config_conf, _ff, indent = 4)
                _ff.close()
            except:
                pass
        self.on_quit_action_actived(None)
        return True
    

class AlDial(Adw.AlertDialog):
    def __init__(self, _parent, _str1):
        super().__init__()
        self._parent = _parent
        # self.set_heading("")
        self.set_body(_str1)
        #
        self.add_response("close", _lang.CLOSE)
        self.connect("response", self.on_close)
        #
        self.present(self._parent)
    
    def on_close(self, _d, _r):
        self.close()


class WinSettings(Adw.Dialog):
    def __init__(self, _parent):
        super().__init__()
        self._parent = _parent
        self.set_name("settingdialog")
        self.set_size_request(800, 300)
        self.set_title(_lang.SETTINGS)
        #
        self.headerbar = Gtk.HeaderBar.new()
        self.headerbar.set_show_title_buttons(False)
        #
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.set_child(self.main_box)
        self.main_box.append(self.headerbar)
        #
        self.stack_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        self.main_box.append(self.stack_box)
        #
        self.stack_sidebar = Gtk.StackSidebar.new()
        self.stack_sidebar.set_vexpand(True)
        self.stack_box.append(self.stack_sidebar)
        #
        btn_apply = Gtk.Button(label=_lang.APPLY)
        btn_apply.connect("clicked", self.on_apply)
        btn_apply.set_css_classes(["suggested-action",""])
        self.headerbar.pack_start(btn_apply)
        #
        btn_close = Gtk.Button(label=_lang.CLOSE)
        btn_close.connect("clicked", self.on_close)
        self.headerbar.pack_end(btn_close)
        #
        self._stack = Gtk.Stack.new()
        self._stack.props.hexpand = True
        self._stack.props.vexpand = True
        self.stack_sidebar.set_stack(self._stack)
        self.stack_box.append(self._stack)
        ############
        box1 = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        #
        self._stack.add_titled(box1,"box1",_lang.PGENERAL)
        bgrid1 = Gtk.Grid.new()
        bgrid1.set_column_homogeneous(False)
        bgrid1.set_hexpand(True)
        bgrid1.set_vexpand(True)
        box1.append(bgrid1)
        # font size
        lbl00 = Gtk.Label(label=_lang.FONTSIZE)
        lbl00.set_halign(Gtk.Align.START)
        bgrid1.attach(lbl00,0,0,1,1)
        self.fontsize_spinbtn = Gtk.SpinButton.new_with_range(4,80,1)
        self.fontsize_spinbtn.set_value(FONTSIZE)
        bgrid1.attach_next_to(self.fontsize_spinbtn,lbl00,1,1,1)
        # font family
        lbl02 = Gtk.Label(label=_lang.FONTFAMILY)
        lbl02.set_halign(Gtk.Align.START)
        bgrid1.attach(lbl02,0,2,1,1)
        self.fontfamily_btn = Gtk.Button(label=FONTFAMILY)
        self.fontfamily_btn.connect("clicked", self.on_font_family)
        bgrid1.attach_next_to(self.fontfamily_btn,lbl02,1,1,1)
        self.new_font_family = None
        # foreground color
        lbl01 = Gtk.Label(label=_lang.FOREGROUNDCOLOR)
        lbl01.set_halign(Gtk.Align.START)
        bgrid1.attach(lbl01,0,3,1,1)
        color_dlg = Gtk.ColorDialog.new()
        self.fcolor_btn = Gtk.ColorDialogButton.new(color_dlg)
        _btn_color = Gdk.RGBA()
        _btn_color.parse(FOREGROUND)
        self.fcolor_btn.set_rgba(_btn_color)
        bgrid1.attach_next_to(self.fcolor_btn,lbl01,1,1,1)
        #
        # background color
        lbl03 = Gtk.Label(label=_lang.BACKGROUNDCOLOR)
        lbl03.set_halign(Gtk.Align.START)
        bgrid1.attach(lbl03,0,4,1,1)
        color_dlg = Gtk.ColorDialog.new()
        self.bcolor_btn = Gtk.ColorDialogButton.new(color_dlg)
        _btn_color = Gdk.RGBA()
        _btn_color.parse(BACKGROUND)
        self.bcolor_btn.set_rgba(_btn_color)
        bgrid1.attach_next_to(self.bcolor_btn,lbl03,1,1,1)
        ########
        self.present(self._parent)
    
    def on_font_family(self, _w):
        global FONTFAMILY
        _fd = Gtk.FontDialog.new()
        _fd.set_modal(True)
        def font_choosed(source_object, res, data):
            try:
                _pango_font_family = _fd.choose_family_finish(res)
            except GLib.GError:
                return
            _font_name = _pango_font_family.get_name()
            self.fontfamily_btn.set_label(_font_name)
            FONTFAMILY = _font_name
        _fd.choose_family(self_main, None, None, font_choosed, None)
    
    def on_apply(self, w):
        global FOREGROUND
        global BACKGROUND
        global FONTFAMILY
        global FONTSIZE
        #
        FONTSIZE = int(self.fontsize_spinbtn.get_value())
        config_conf["textsize"] = FONTSIZE
        #
        FOREGROUND = self.fcolor_btn.get_rgba().to_string()
        config_conf["foreground"] = FOREGROUND
        #
        BACKGROUND = self.bcolor_btn.get_rgba().to_string()
        config_conf["background"] = BACKGROUND
        #
        FONTFAMILY = self.fontfamily_btn.get_label()
        config_conf["fontfamily"] = FONTFAMILY
        #
        self._parent.set_custom_settings(FOREGROUND, BACKGROUND, FONTSIZE, FONTFAMILY)
        try:
            _ff =  open(os.path.join(HOME_CONFIG,"configs/config.json"), "w")
            json.dump(config_conf, _ff, indent = 4)
            _ff.close()
        except Exception as E:
            AlDial(self_main, str(E))
        #
        self.close()
    
    def on_close(self, w):
        self.close()


class MyApp(Adw.Application):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._files = None

    def do_activate(self):
        active_window = self.props.active_window
        if active_window:
            active_window.present()
        else:
            self.win = MainWindow(application=self, _files=self._files)
            self.win.present()
    
    def do_open(self, _files, n_files, _data):
        if n_files > 0:
            self._files = _files[0]
        self.activate()

app = MyApp(application_id="com.Paperless.epubreader",flags= Gio.ApplicationFlags.HANDLES_OPEN)
_app = app
app.run(sys.argv)