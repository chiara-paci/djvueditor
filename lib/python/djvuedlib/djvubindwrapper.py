#       This module is a copy&paste from djvubind main (BASE_DIR/opt/djvubind/bin/djvubind),
#       with some adjustment to make a library function from it.

#       This program is free software; you can redistribute it and/or modify
#       it under the terms of the GNU General Public License as published by
#       the Free Software Foundation; either version 3 of the License, or
#       (at your option) any later version.
#
#       This program is distributed in the hope that it will be useful,
#       but WITHOUT ANY WARRANTY; without even the implied warranty of
#       MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#       GNU General Public License for more details.
#
#       You should have received a copy of the GNU General Public License
#       along with this program; if not, write to the Free Software
#       Foundation, Inc.

import optparse
import os
import queue
import shutil
import sys
import threading
import time
import concurrent.futures

import djvubind.utils

from . import book as libbook
from . import ocr as libocr
from . import encode as libencode

class Project:
    """
    Abstraction of the entire project.  This should make things like status
    reports, clean exits on errors, and access to information a little easier.
    """

    def __init__(self, book, opts, config_file):
        self.get_config(opts,config_file)

        self.out = os.path.abspath('book.djvu')

        self.book=book
        self.ocr = libocr.Tesseract(self.opts['tesseract_options'])
        self.enc = libencode.Encoder(self.opts)

    def bind(self):
        """
        Fully encodes all images into a single djvu file.  This includes adding
        known ocr information, covers, metadata, etc.
        """
        self.enc.enc_book(self.book, self.out)

    def get_config(self, opts, config_file):
        """
        Retrives configuration options set in the user's config file.  Options
        passed through the command line (already in 'opts') should be
        translated and overwrite config file options.
        """

        # Set default options
        self.opts = {'cores':-1,
                     'ocr':True,
                     'ocr_engine':'tesseract',
                     'cuneiform_options':'',
                     'tesseract_options':'',
                     'bitonal_encoder':'cjb2',
                     'color_encoder':'csepdjvu',
                     'c44_options':'',
                     'cjb2_options':'-lossless',
                     'cpaldjvu_options':'',
                     'csepdjvu_options':'',
                     'minidjvu_options':'--lossy -pages-per-dict 100',
                     'win_path':'C:\\Program Files\\DjVuZone\\DjVuLibre\\'}

        # filename = '/etc/djvubind/config'
        if os.path.isfile(config_file):
            config_opts = djvubind.utils.parse_config(config_file)
            self.opts.update(config_opts)

        # Set cetain variables to the proper type
        self.opts['cores'] = int(self.opts['cores'])
        self.opts['ocr'] = (self.opts['ocr'] == 'True')

        # Overwrite or create values for certain command line options
        if opts.no_ocr:
            self.opts['ocr'] = False
        if opts.ocr_engine is not None:
            self.opts['ocr_engine'] = opts.ocr_engine
        if opts.tesseract_options is not None:
            self.opts['tesseract_options'] = opts.tesseract_options
        if opts.cuneiform_options is not None:
            self.opts['cuneiform_options'] = opts.cuneiform_options

        if opts.title_start:
            self.opts['title_start'] = opts.title_start
        if opts.title_start_number:
            self.opts['title_start_number'] = opts.title_start_number
        for special in opts.title_exclude:
            if ':' in special:
                special = special.split(':')
                self.opts['title_exclude'][special[0]] = special[1]
            else:
                self.opts['title_exclude'][special] = None
        self.opts['title_uppercase'] = opts.title_uppercase

        # Detect number of cores if not manually set already
        if self.opts['cores'] == -1:
            self.opts['cores'] = djvubind.utils.cpu_count()

        #if self.opts['verbose']:
        print('Executing with these parameters:')
        print(self.opts)
        print('')

    def _apply_ocr(self,page):
        boxing = self.ocr.analyze(page)
        page.text = libocr.translate(boxing)
        return page.text

    def get_ocr(self,max_threads):
        if max_threads==1:
            for page in self.book.pages:
                self._apply_ocr(page)
            return

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_threads) as executor:
            # Start the load operations and mark each future with its URL
            future_to_page = {executor.submit(self._apply_ocr, page): page for page in self.book.pages}
            for future in concurrent.futures.as_completed(future_to_page):
                page = future_to_page[future]
                try:
                    data = future.result()
                except Exception as exc:
                    print('Page %s generated an exception: %s' % (page.title, exc))
                else:
                    print('Page %s is %d bytes' % (page.title, len(data)))

def djvubind_main(config_file,file_list,djvu_name,max_threads):
    argv=["djvubind"]
    parser = optparse.OptionParser("", version="1", description="")
    parser.set_defaults(no_ocr=False, ocr_engine=None, 
                        tesseract_options=None, cuneiform_options=None,
                        title_start=False, title_start_number=1, 
                        title_exclude=[], title_uppercase=False)
    parser.add_option("--no-ocr", action="store_true", dest="no_ocr", help="Images will not be processed for text content.")
    parser.add_option("--ocr-engine", dest="ocr_engine", help="Select which ocr engine to use (cuneiform|tesseract).  By default, '%default' is used.")
    parser.add_option("--tesseract-options", dest="tesseract_options", help="Additional command line options to pass to tesseract.")
    parser.add_option("--cuneiform-options", dest="cuneiform_options", help="Additional command line options to pass to cuneiform.")

    (options, args) = parser.parse_args(argv)

    print(options,args)


    ######################
    # Load pages

    # Add files to the project
    print('{0} Collecting files to be processed.'.format(djvubind.utils.color('*', 'green')))

    book=libbook.Book()
    book.set_pages(file_list)

    if len(book.pages) == 0: return
    print('  Binding a total of {0} file(s).'.format(len(book.pages)))

    proj = Project(book,options,config_file)
    proj.out=os.path.abspath(djvu_name)

    ######################
    # Process

    print('{0} Performing optical character recognition.'.format(djvubind.utils.color('*', 'green')))
    proj.get_ocr(max_threads)

    #proj.book.save_report()

    print('{0} Encoding all information to {1}.'.format(djvubind.utils.color('*', 'green'), proj.out))

    enc_opts={
        "ocr": True,
        'bitonal_encoder': proj.opts["bitonal_encoder"], # minidjvu, cjb2
        'color_encoder': proj.opts["color_encoder"], # c44,csepdjvu,cpaldjvu
        'c44_options': proj.opts["c44_options"],
        'cjb2_options': proj.opts["cjb2_options"],
        'cpaldjvu_options': proj.opts["cpaldjvu_options"],
        'csepdjvu_options': proj.opts["csepdjvu_options"],
        'minidjvu_options': proj.opts["minidjvu_options"],
    }

    enc = libencode.Encoder(enc_opts)

    enc.enc_book(proj.book, proj.out)



