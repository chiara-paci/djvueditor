import os
import sys
import wand.image
import traceback

#from djvubind import utils

from . import ocr as libocr
from . import hiddentext

import os.path
import concurrent.futures


class Book:
    """
    Contains all information regarding the djvu ebook that will be produced.
    """

    def __init__(self):
        self.pages = []
        self.cover_front = None
        self.cover_back = None

        self.suppliments = {
            'metadata':None,
            'bookmarks':None
        }
        self.dpi = 0

    def set_pages(self,file_list):
        for fpath,ftype,title in file_list:
            if ftype=="cover_front":
                self.cover_front=Cover(fpath)
                continue
            if ftype=="cover_back":
                self.cover_back=Cover(fpath)
                continue
            if ftype!="page":
                self.suppliments[ftype]=fpath
                continue
            page=Page(fpath)
            page.title=title
            if (self.dpi) and (page.dpi != self.dpi):
                print("msg: [organizer.Book.analyze()] {0}".format(page.path))
                print("     Page dpi is different from the previous page.", file=sys.stderr)
                print("     If you encounter problems with minidjvu, this is probably why.", file=sys.stderr)
            self.dpi = max(self.dpi,page.dpi)
            self.pages.append(page)

    def save_report(self):
        """
        Saves a diagnostic report of the book in csv format.
        """
        with open('book.csv', 'w', encoding='utf8') as handle:
            handle.write('Path, Bitonal, DPI, Title, OCR\n')
            for page in self.pages:
                entry = [page.path, str(page.bitonal), str(page.dpi), str(page.title), str(len(page.text))]
                entry = ", ".join(entry)
                handle.write(entry)
                handle.write('\n')

    def apply_ocr(self,ocr,max_threads):
        def ocr_on_page(page):
            return page.apply_ocr(ocr)

        if max_threads==1:
            for page in self.pages:
                ocr_on_page(page)
            return

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_threads) as executor:
            # Start the load operations and mark each future with its URL
            future_to_page = {executor.submit(ocr_on_page, page): page for page in self.pages}
            for future in concurrent.futures.as_completed(future_to_page):
                page = future_to_page[future]
                try:
                    data = future.result()
                except Exception as e:
                    print('Page %s generated an exception: %s' % (page.title, e))
                    traceback.print_exc()
                else:
                    print('Page %s is %d bytes' % (page.title, len(data)))
        

class Cover(object):
    def __init__(self, path):
        self.path = os.path.abspath(path)
        with wand.image.Image.ping(filename=self.path) as img:
            self.dpi=int(img.resolution[0])
            self.depth=img.depth
            self.bitonal=(self.depth==1)
            self.height=img.height
            self.width=img.width
            self.format=img.format


class Page(object):
    """
    Contains information relevant to a single page/image.
    """

    def __init__(self, path):
        self.path = os.path.abspath(path)
        t = self.path.split(".")
        self.basepath=".".join(t[:-1]) # path without suffix
        self._text_path="%s.txt" % self.basepath
        self._text_cache=None
        self._text_structure=None

        with wand.image.Image.ping(filename=self.path) as img:
            self.dpi=int(img.resolution[0])
            self.depth=img.depth
            self.bitonal=(self.depth==1)
            self.height=img.height
            self.width=img.width
            self.format=img.format
 
        self.title = None

        if self.bitonal and (self.path[-4:].lower() == '.pgm'):
            msg = "wrn: {0}: Bitonal image but using a PGM format instead of PBM. Tesseract might get mad!".format(os.path.split(self.path)[1])
            print(msg, file=sys.stderr)

    def _load_text(self):
        if self._text_cache is not None:
            return
        try:
            with open(self._text_path,'r') as fd:
                self._text_cache=fd.read()
            self._text_structure=hiddentext.djvused_parse_text(self._text_cache)
        except IOError as e:
            self._text_cache=None
            self._text_structure=None
            return

    def _get_text(self):
        self._load_text()
        return self._text_cache

    def _set_text(self, val):
        self._text_cache=val
        self._text_structure=hiddentext.djvused_parse_text(val)
        with open(self._text_path, 'w') as fd:
            fd.write(self._text_cache)

    text=property(_get_text,_set_text)

    @property
    def text_structure(self):
        self._load_text()
        return self._text_structure

    def reload_text(self):
        try:
            with open(self._text_path,'r') as fd:
                self._text_cache=fd.read()
            self._text_structure=hiddentext.djvused_parse_text(self._text_cache)
        except IOError as e:
            self._text_cache=None
            self._text_structure=None
            return

    def save_text_structure(self):
        txt=self._text_structure.out_tree()
        self._text_cache=txt
        with open(self._text_path, 'w') as fd:
            fd.write(self._text_cache)

    def apply_ocr(self,ocr):
        if os.path.exists(self._text_path): return self.text
        boxing = ocr.analyze(self)
        self.text = libocr.translate(boxing)
        return self.text
        
    def insert_text_rules(self,parent,ind,count):
        if self._text_structure is None: return
        return self._text_structure.insert_rules(parent,ind,count)

    def remove_text_rules(self,parent,ind,count):
        if self._text_structure is None: return
        return self._text_structure.remove_rules(parent,ind,count)

    def index_text_rule(self,obj):
        if self._text_structure is None: return None
        return self._text_structure.index(obj)
         
    def duplicate_text_rule(self,obj):
        if self._text_structure is None: return None
        return self._text_structure.duplicate_rule(obj)

    def create_text_rule(self,parent,level,xmin,ymin,xmax,ymax,text):
        if self._text_structure is None: return None
        return self._text_structure.create_rule(parent,level,xmin,ymin,xmax,ymax,text)

    def merge_above_text_rule(self,obj):
        if self._text_structure is None: return None
        return self._text_structure.merge_above_rule(obj)
         
    def merge_below_text_rule(self,obj):
        if self._text_structure is None: return None
        return self._text_structure.merge_below_rule(obj)
         
    def count_children_text_rule(self,obj):
        if self._text_structure is None: return 0
        return self._text_structure.count_children(obj)

    def get_text_rule(self,parent,ind):
        if self._text_structure is None: return None
        return self._text_structure.get_rule(parent,ind)

    def split_rule(self,obj,splitted):
        if self._text_structure is None: return None
        return self._text_structure.split_rule(obj,splitted)

    def shift_down_text_rule(self,obj,val):
        if self._text_structure is None: return None
        return self._text_structure.shift_down_rule(obj,val)

    def shift_up_text_rule(self,obj,val):
        if self._text_structure is None: return None
        return self._text_structure.shift_up_rule(obj,val)

    def shift_right_text_rule(self,obj,val):
        if self._text_structure is None: return None
        return self._text_structure.shift_right_rule(obj,val)

    def shift_left_text_rule(self,obj,val):
        if self._text_structure is None: return None
        return self._text_structure.shift_left_rule(obj,val)

    def move_up(self,obj):
        if self._text_structure is None: return None
        return self._text_structure.move_up(obj)

    def move_down(self,obj):
        if self._text_structure is None: return None
        return self._text_structure.move_down(obj)

    def move_left(self,obj):
        if self._text_structure is None: return None
        return self._text_structure.move_left(obj)

    def move_right(self,obj):
        if self._text_structure is None: return None
        return self._text_structure.move_right(obj)

