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
#       Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#       MA 02110-1301, USA.
"""
Contains code relevant to encoding images and metadata into a djvu format.
"""

import glob
import os
import shutil
import sys
import wand.image
import wand.color
import subprocess

from djvubind import utils

class ExternalEncoder(object):
    def __init__(self,options):
        self._options=options
        self._temporary_files=[]

    # ImageMagick convert

    def _convert(self,dst_format,src_path,dst_path):
        with wand.image.Image(filename=src_path) as img:
            img.format = dst_format
            img.save(filename=dst_path)

    def _extract_graphics(self,dst_format,src_path,dst_path):
        with wand.image.Image(filename=src_path) as img:
           img.opaque_paint(target=wand.color.Color("black"),fill=wand.color.Color("white"))
           img.format = dst_format
           img.save(filename=dst_path)

    def _extract_textual(self,dst_format,src_path,dst_path):
        with wand.image.Image(filename=src_path) as img:
           img.opaque_paint(target=wand.color.Color("black"),fill=wand.color.Color("white"),invert=True)
           img.depth = 1
           img.format = dst_format
           img.type = "bilevel"
           img.save(filename=dst_path)

    # generic command

    def _exec(self,cmd):
        if type(cmd) is str:
            ret=subprocess.run(cmd,shell=True)
        else:
            ret=subprocess.run(cmd)
        if ret.returncode == 0: return
        if ret.returncode < 0:
            print("err: Process killed: %s" % cmd, file=sys.stderr)
            return
        print("err: Process %s exit with status %s" % (cmd,ret.returncode), file=sys.stderr)

    # djvm

    def _djvm_insert(self,doc,page,pagenum=None):
        if not os.path.isfile(doc):
            shutil.copy(page, doc)
            return
        cmd=['djvm', '-i', doc, page]
        if pagenum is not None: cmd.append(pagenum)
        self._exec(cmd)


    ###############

    def _clean_infile(self,infile,dpi): return infile

    def _cleanup(self):
        for f in self._temporary_files:
            if os.path.isfile(f): os.remove(f)
            self._temporary_files.remove(f)

    def _action(self,infile,outfile,dpi): pass

    def __call__(self, infile, outfile, dpi):
        infile=self._clean_infile(infile,dpi)
        self._action(infile,outfile,dpi)
        # Check that the outfile has been created.
        if not os.path.isfile(outfile):
            msg = 'err: No encode errors, but "{0}" does not exist!'.format(outfile)
            print(msg, file=sys.stderr)
            #sys.exit(1)
        self._cleanup()

class C44Encoder(ExternalEncoder):

    def _clean_infile(self,infile,dpi):
        extension = infile.split('.')[-1]
        if extension in ['pgm', 'ppm', 'jpg', 'jpeg']: return infile
        self._convert("PPM",infile,"temp.ppm")
        self._temporary_files.append("temp.ppm")
        return "temp.ppm"

    def _action(self,infile,outfile,dpi):
        cmd = 'c44 -dpi {0} {1} "{2}" "{3}"'.format(dpi, self._options, infile, outfile)
        self._exec(cmd)
        
class Cjb2Encoder(ExternalEncoder):
    def _clean_infile(self,infile,dpi):
        extension = infile.split('.')[-1]
        if extension in ['tif','tiff','pbm','pgm','pnm','rle']: return infile
        self._convert("PBM",infile,"temp.pbm")
        self._temporary_files.append("temp.pbm")
        return "temp.pbm"

    def _action(self,infile,outfile,dpi):
        # cjb2 will not process images if dpi is greater than 1200 or less than 25, and will exit.
        # If -dpi is simply not specified it will process the image.
        # This limitation apparently has to do with some of their algorithms to despeckle and whatenot.
        if (dpi <= 25) or (dpi >= 1200):
            cmd = 'cjb2 {0} "{1}" "{2}"'.format(self._options, infile, outfile)
        else:
            cmd = 'cjb2 -dpi {0} {1} "{2}" "{3}"'.format(dpi, self._options, infile, outfile)

        self._exec(cmd)

class CpaldjvuEncoder(ExternalEncoder):
    def _clean_infile(self,infile,dpi):
        extension = infile.split('.')[-1]
        if extension in ['ppm']: return infile
        self._convert("PPM",infile,"temp.ppm")
        self._temporary_files.append("temp.ppm")
        return "temp.ppm"

    def _action(self,infile,outfile,dpi):
        cmd = 'cpaldjvu -dpi {0} {1} "{2}" "{3}"'.format(dpi, self._options, infile, outfile)
        self._exec(cmd)

class CsepdjvuEncoder(ExternalEncoder):
    def __init__(self,options,cjb2_options):
        ExternalEncoder.__init__(self,options)
        self._cjb2=Cjb2Encoder(cjb2_options)

    def _clean_infile(self,infile,dpi):
        # Separate the bitonal text (scantailor's mixed mode) from everything else.
        self._extract_graphics("PPM",infile,"temp_graphics.ppm")
        self._extract_textual("PBM",infile,"temp_textual.pbm")

        self._cjb2('temp_textual.pbm', 'enc_bitonal_out.djvu', dpi)

        # Encode with color with bitonal via csepdjvu
        self._exec(['ddjvu','-format=rle','-v', "enc_bitonal_out.djvu", "temp_textual.rle"])

        with open('temp_merge.mix', 'wb') as mix:
            with open('temp_textual.rle', 'rb') as rle:
                buffer = rle.read(1024)
                while buffer:
                    mix.write(buffer)
                    buffer = rle.read(1024)
            with open('temp_graphics.ppm', 'rb') as ppm:
                buffer = ppm.read(1024)
                while buffer:
                    mix.write(buffer)
                    buffer = ppm.read(1024)

        self._temporary_files+=[
            "temp_graphics.ppm",
            'temp_textual.pbm', 
            'enc_bitonal_out.djvu',
            "temp_textual.rle", "temp_merge.mix" 
        ]

        return "temp_merge.mix"

    def _action(self, infile, outfile, dpi):
        self._exec('csepdjvu -d {0} {1} "temp_merge.mix" "temp_final.djvu"'.format(dpi, self._options))
        #self._exec('djvm -i {0} "temp_final.djvu"'.format(outfile))
        self._djvm_insert(outfile,"temp_final.djvu")
        self._temporary_files.append("temp_final.djvu")

class Encoder:
    """
    An intelligent djvu super-encoder that can work with numerous djvu encoders.
    """

    def __init__(self, opts):
        self.opts = opts

        print(self.opts)

        self.dep_check()

        self._c44=C44Encoder(self.opts['c44_options'])
        self._cjb2=Cjb2Encoder(self.opts['cjb2_options'])
        self._cpaldjvu=CpaldjvuEncoder(self.opts['cpaldjvu_options'])
        self._csepdjvu=CsepdjvuEncoder(self.opts['csepdjvu_options'],self.opts["cjb2_options"])

    def dep_check(self):
        """
        Check for ocr engine availability.
        """

        if not utils.is_executable(self.opts['bitonal_encoder']):
            msg = 'err: encoder "{0}" is not installed.'.format(self.opts['bitonal_encoder'])
            print(msg, file=sys.stderr)
            sys.exit(1)
        if not utils.is_executable(self.opts['color_encoder']):
            msg = 'err: encoder "{0}" is not installed.'.format(self.opts['color_encoder'])
            print(msg, file=sys.stderr)
            sys.exit(1)

        return None


    def _minidjvu(self, infiles, outfile, dpi):
        """
        Encode files with minidjvu.
        N.B., minidjvu is the only encoder function that expects a list a filenames
        and not a string with a single filename.  This is because minidjvu gains
        better compression with a shared dictionary across multiple images.
        """

        # Specify filenames that will be used.
        tempfile = 'enc_temp.djvu'

        temp_files = []
        for filename in infiles:
            extension = filename.split('.')[-1].lower()
            if extension not in ['tif','tiff','pbm','pnm']:
                temp_files.append(filename+'.pbm')
        if len(temp_files) != 0:
            print("msg: Files were found that are bitonal but in formats not accepted by minidjvu. They will be listed below.", file=sys.stderr)
            print("     Copying to PBM format to be compatible - this may produce a large temporary file or files!", file=sys.stderr)
            for replacement in temp_files:
                print("     {0}".format(replacement[:-4]), file=sys.stderr)
                #utils.execute('convert {0} {1}'.format(replacement[:-4], replacement))
                #index = infiles.index(replacement[:-4])
                #infiles.remove(replacement[:-4])
                #infiles.insert(index, replacement)
            msg = utils.color("!!!: Automatic conversion of minidjvu files is disabled, because the above list could be *very* long and PBM files are not small.", "red")
            print(msg, file=sys.stderr)
            print("     minidjvu will accept PBM, PNM, and TIF files. Convert by hand before proceeding.", file=sys.stderr)
            sys.exit(1)

        # Minidjvu has to worry about the length of the command since all the filenames are
        # listed.
        cmds = utils.split_cmd('minidjvu -d {0} {1}'.format(dpi, self.opts['minidjvu_options']), infiles, tempfile)

        # Execute each command, adding each result into a single, multipage djvu.
        for cmd in cmds:
            utils.execute(cmd)
            self.djvu_insert(tempfile, outfile)

        os.remove(tempfile)
        for replacement in temp_files:
            os.remove(replacement)

        return None


    def djvu_insert(self, infile, djvufile, page_num=None):
        """
        Insert a single page djvu file into a multipage djvu file.  By default it will be
        placed at the end, unless page_num is specified.
        """
        if (not os.path.isfile(djvufile)):
            shutil.copy(infile, djvufile)
        elif page_num is None:
            utils.execute('djvm -i "{0}" "{1}"'.format(djvufile, infile))
        else:
            utils.execute('djvm -i "{0}" "{1}" {2}'.format(djvufile, infile, int(page_num)))

    def enc_book(self, book, outfile):
        """
        Encode pages, metadata, etc. contained within a organizer.Book() class.
        """

        tempfile = 'temp.djvu'

        # Encode bitonal images first, mainly because of minidjvu needing to do
        # them all at once.
        if self.opts['bitonal_encoder'] == 'minidjvu':
            bitonals = []
            for page in book.pages:
                if page.bitonal:
                    filepath = os.path.split(page.path)[1]
                    bitonals.append(filepath)
            if len(bitonals) > 0:
                if self.opts['bitonal_encoder'] == 'minidjvu':
                    self._minidjvu(bitonals, tempfile, book.dpi)
                    self.djvu_insert(tempfile, outfile)
                    os.remove(tempfile)
                    #self.progress()
        elif self.opts['bitonal_encoder'] == 'cjb2':
            for page in book.pages:
                if page.bitonal:
                    self._cjb2(page.path, tempfile, page.dpi)
                    self.djvu_insert(tempfile, outfile)
                    os.remove(tempfile)
                    #self.progress()
        else:
            for page in book.pages:
                if not page.bitonal:
                    msg = 'wrn: Invalid bitonal encoder.  Bitonal pages will be omitted.'
                    msg = utils.color(msg, 'red')
                    print(msg, file=sys.stderr)
                    break

        # Encode and insert non-bitonal
        if self.opts['color_encoder'] == 'csepdjvu':
            for page in book.pages:
                if not page.bitonal:
                    page_number = book.pages.index(page) + 1
                    print("A",page_number,page.path)
                    self._csepdjvu(page.path, tempfile, page.dpi)
                    self.djvu_insert(tempfile, outfile, page_number)
                    os.remove(tempfile)
                    #self.progress()
        elif self.opts['color_encoder'] == 'c44':
            for page in book.pages:
                if not page.bitonal:
                    page_number = book.pages.index(page) + 1
                    self._c44(page.path, tempfile, page.dpi)
                    self.djvu_insert(tempfile, outfile, page_number)
                    os.remove(tempfile)
                    #self.progress()
        elif self.opts['color_encoder'] == 'cpaldjvu':
            for page in book.pages:
                if not page.bitonal:
                    page_number = book.pages.index(page) + 1
                    self._cpaldjvu(page.path, tempfile, page.dpi)
                    self.djvu_insert(tempfile, outfile, page_number)
                    os.remove(tempfile)
                    #self.progress()
        else:
            for page in book.pages:
                if not page.bitonal:
                    msg = 'wrn: Invalid color encoder.  Colored pages will be omitted.'
                    msg = utils.color(msg, 'red')
                    print(msg, file=sys.stderr)
                    break

        # Add ocr data
        if self.opts['ocr']:
            for page in book.pages:
                handle = open('ocr.txt', 'w', encoding="utf8")
                handle.write(page.text)
                handle.close()
                page_number = book.pages.index(page) + 1
                utils.simple_exec('djvused -e "select {0}; remove-txt; set-txt \'ocr.txt\'; save" "{1}"'.format(page_number, outfile))
                os.remove('ocr.txt')

        # Insert front/back covers, metadata, and bookmarks
        if book.suppliments['cover_front'] is not None:
            dpi = int(utils.execute('identify -ping -format %x "{0}"'.format(book.suppliments['cover_front']), capture=True).decode('ascii').split(' ')[0])
            self._c44(book.suppliments['cover_front'], tempfile, dpi)
            self.djvu_insert(tempfile, outfile, 1)
            utils.execute('djvused -e "select 1; set-page-title cover; save" "{0}"'.format(outfile))
        if book.suppliments['cover_back'] is not None:
            dpi = int(utils.execute('identify -ping -format %x "{0}"'.format(book.suppliments['cover_back']), capture=True).decode('ascii').split(' ')[0])
            self._c44(book.suppliments['cover_back'], tempfile, dpi)
            self.djvu_insert(tempfile, outfile, -1)
        if book.suppliments['metadata'] is not None:
            utils.simple_exec('djvused -e "set-meta {0}; save" "{1}"'.format(book.suppliments['metadata'], outfile))
        if book.suppliments['bookmarks'] is not None:
            utils.simple_exec('djvused -e "set-outline {0}; save" "{1}"'.format(book.suppliments['bookmarks'], outfile))

        script = ''
        index = 1
        if book.suppliments['cover_front'] is not None:
            script += 'select '+str(index)+'; set-page-title "cover";\n'
            index = index + 1
        for page in book.pages:
            if page.title is None:
                index = index + 1
            else:
                script += 'select '+str(index)+'; set-page-title "'+str(page.title)+'";\n'
                index = index + 1
        if book.suppliments['cover_back'] is not None:
            script += 'select '+str(index)+'; set-page-title "back cover";\n'
        script += 'save'
        with open('titles', 'w') as handle:
            handle.write(script)
        utils.simple_exec('djvused -f titles "{0}"'.format(outfile))
        os.remove('titles')

        if os.path.isfile(tempfile):
            os.remove(tempfile)

        return None
