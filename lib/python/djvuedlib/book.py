import os
import sys
import wand.image
import traceback
import grako.exceptions

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
        self.pages_by_path={}
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
            self.pages_by_path[page.path]=page

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


def read_text_structure_decorator(func):
    def decorated(self,*args,**kwargs):
        if self._text_structure is None: return None
        ret=func(self,*args,**kwargs)
        return ret
    return decorated

def text_structure_decorator(func):
    def decorated(self,*args,**kwargs):
        print("decorated!!!")
        if self._text_structure is None: return None
        ret=func(self,*args,**kwargs)
        self.save_text_structure()
        return ret
    return decorated

class Page(object):
    """
    Contains information relevant to a single page/image.
    """

    def __str__(self):
        label=os.path.basename(self.path)
        if self.title is not None:
            label="[%s] %s" % (self.title,label)
        return label

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
        except grako.exceptions.FailedToken as e:
            self._text_structure=None
            print("Grako error:",self._text_path)

    def _get_text(self):
        self._load_text()
        return self._text_cache

    def _set_text(self, val):
        self._text_cache=val
        with open(self._text_path, 'w') as fd:
            fd.write(self._text_cache)
        try:
            self._text_structure=hiddentext.djvused_parse_text(val)
        except grako.exceptions.FailedToken as e:
            self._text_structure=None
            print("Grako error:",self._text_path)


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
        print("Save!")
        self._text_cache=txt
        with open(self._text_path, 'w') as fd:
            fd.write(self._text_cache)

    def apply_ocr(self,ocr):
        if os.path.exists(self._text_path): return self.text
        boxing = ocr.analyze(self)
        self.text = libocr.translate(boxing)
        return self.text

    ###

    @read_text_structure_decorator
    def index_text_rule(self,obj):
        # if self._text_structure is None: return None
        return self._text_structure.index(obj)

    @read_text_structure_decorator
    def count_children_text_rule(self,obj):
        # if self._text_structure is None: return 0
        return self._text_structure.count_children(obj)

    @read_text_structure_decorator
    def get_text_rule(self,parent,ind):
        # if self._text_structure is None: return None
        return self._text_structure.get_rule(parent,ind)

    @text_structure_decorator
    def insert_text_rules(self,parent,ind,count):
        # if self._text_structure is None: return
        return self._text_structure.insert_rules(parent,ind,count)

    @text_structure_decorator
    def remove_text_rules(self,parent,ind,count):
        # if self._text_structure is None: return
        return self._text_structure.remove_rules(parent,ind,count)
         
    @text_structure_decorator
    def duplicate_text_rule(self,obj):
        # if self._text_structure is None: return None
        return self._text_structure.duplicate_rule(obj)

    @text_structure_decorator
    def create_text_rule(self,parent,level,xmin,ymin,xmax,ymax,text):
        # if self._text_structure is None: return None
        return self._text_structure.create_rule(parent,level,xmin,ymin,xmax,ymax,text)

    @text_structure_decorator
    def merge_above_text_rule(self,obj):
        # if self._text_structure is None: return None
        return self._text_structure.merge_above_rule(obj)
         
    @text_structure_decorator
    def merge_below_text_rule(self,obj):
        # if self._text_structure is None: return None
        return self._text_structure.merge_below_rule(obj)
         
    @text_structure_decorator
    def split_rule(self,obj,splitted):
        # if self._text_structure is None: return None
        return self._text_structure.split_rule(obj,splitted)

    @text_structure_decorator
    def shift_down_text_rule(self,obj,val):
        # if self._text_structure is None: return None
        return self._text_structure.shift_down_rule(obj,val)

    @text_structure_decorator
    def shift_up_text_rule(self,obj,val):
        # if self._text_structure is None: return None
        return self._text_structure.shift_up_rule(obj,val)

    @text_structure_decorator
    def shift_right_text_rule(self,obj,val):
        # if self._text_structure is None: return None
        return self._text_structure.shift_right_rule(obj,val)

    @text_structure_decorator
    def shift_left_text_rule(self,obj,val):
        # if self._text_structure is None: return None
        return self._text_structure.shift_left_rule(obj,val)

    @text_structure_decorator
    def move_up(self,obj):
        # if self._text_structure is None: return None
        return self._text_structure.move_up(obj)

    @text_structure_decorator
    def move_down(self,obj):
        # if self._text_structure is None: return None
        return self._text_structure.move_down(obj)

    @text_structure_decorator
    def move_left(self,obj):
        # if self._text_structure is None: return None
        return self._text_structure.move_left(obj)
    
    @text_structure_decorator
    def move_right(self,obj):
        # if self._text_structure is None: return None
        return self._text_structure.move_right(obj)


