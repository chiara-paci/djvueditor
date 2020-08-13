import os
import sys
import wand.image

#from djvubind import utils

class Book:
    """
    Contains all information regarding the djvu ebook that will be produced.
    """

    def __init__(self):
        self.pages = []
        self.suppliments = {
            'cover_front':None,
            'cover_back':None,
            'metadata':None,
            'bookmarks':None
        }
        self.dpi = None

    def set_pages(self,file_list):
        for fpath,ftype,title in file_list:
            if ftype!="page":
                self.suppliments[ftype]=fpath
                continue
            page=Page(fpath)
            page.title=title
            if (self.dpi is not None) and (page.dpi != self.dpi):
                print("msg: [organizer.Book.analyze()] {0}".format(page.path))
                print("     Page dpi is different from the previous page.", file=sys.stderr)
                print("     If you encounter problems with minidjvu, this is probably why.", file=sys.stderr)
            self.dpi = page.dpi
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

class Page:
    """
    Contains information relevant to a single page/image.
    """

    def __init__(self, path):
        self.path = os.path.abspath(path)
        t = self.path.split(".")
        self.basepath=".".join(t[:-1]) # path without suffix

        with wand.image.Image.ping(filename=self.path) as img:
            self.dpi=int(img.resolution[0])
            self.depth=img.depth
            self.bitonal=(self.depth==1)
            self.height=img.height
            self.width=img.width
            self.format=img.format
            
        self.text = ''
        self.title = None

        if self.bitonal and (self.path[-4:].lower() == '.pgm'):
            msg = "wrn: {0}: Bitonal image but using a PGM format instead of PBM. Tesseract might get mad!".format(os.path.split(self.path)[1])
            print(msg, file=sys.stderr)
