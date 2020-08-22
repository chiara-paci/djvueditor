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
import shlex

class DjvuFile(object):
    def __init__(self,fname):
        if type(fname) is str:
            self._path=fname
        else:
            self._path=fname._path

    def __str__(self): return self._path

    def _exec(self,cmd,**kwargs):
        if type(cmd) is str:
            ret=subprocess.run(cmd,shell=True,**kwargs)
        else:
            ret=subprocess.run(cmd,**kwargs)
        if ret.returncode == 0: return ret.stdout
        if ret.returncode < 0:
            print("err: Process killed: %s" % cmd, file=sys.stderr)
            return ret.stdout
        print("err: Process %s exit with status %s" % (cmd,ret.returncode), file=sys.stderr)
        return ret.stdout

    def insert(self,page,pagenum=None):
        if type(page) is str:
            o_path=page
        else:
            o_path=page._path
        if not os.path.isfile(self._path):
            shutil.copy(o_path, self._path)
            return
        cmd=['djvm', '-i', self._path, o_path]
        if pagenum is not None: cmd.append(str(pagenum))
        self._exec(cmd)

    def __len__(self):
        cmd=["djvused","-e","n",self._path]
        ret=self._exec(cmd,capture_output=True)
        return int(ret)

    def _djvused(self,sedcmd):
        cmd=["djvused","-e",sedcmd,self._path]
        self._exec(cmd)

    def add_text(self,ftxt,page_number):
        sedcmd="select %d; remove-txt; set-txt '%s'; save" % (page_number,ftxt)
        self._djvused(sedcmd)

    def add_cover_front(self,fcover):
        self.insert(fcover,1)
        sedcmd="select 1; set-page-title cover; save"
        self._djvused(sedcmd)

    def add_cover_back(self,fcover):
        self.insert(fcover)
        sedcmd="select %d; set-page-title back; save" % len(self)
        self._djvused(sedcmd)

    def add_metadata(self,fmetadata):
        sedcmd="set-meta %s; save" % fmetadata 
        self._djvused(sedcmd)

    def add_bookmarks(self,fbookmarks):
        sedcmd="set-outline %s; save" % fbookmarks
        self._djvused(sedcmd)

    def _djvused_script(self,script):
        cmd=["djvused",self._path]
        self._exec(cmd,input=script.encode())

    def add_pages_number(self,desc):
        script=""
        for page_id,title in desc:
            script += 'select %s; set-page-title "%s";\n' % (page_id,title)
        script+="save"
        self._djvused_script(script)

    def set_thumbnails(self,size):
        sedcmd="set-thumbnails %d; save" % size
        self._djvused(sedcmd)
        

class ExternalEncoder(object):
    bitonal = False

    class ProcessKilledException(Exception): pass
    class ProcessExitWithErrorsException(Exception): pass

    def __init__(self,options):
        self._options=shlex.split(options)
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
            ret=subprocess.run(cmd,shell=True,capture_output=True)
        else:
            ret=subprocess.run(cmd,capture_output=True)
        if ret.returncode == 0: return
        if ret.returncode < 0:
            raise self.ProcessKilledException("err: Process killed: %s" % cmd)
        msg="err: Process %s exit with status %s\n" % (cmd,ret.returncode)
        msg+="STDOUT: "
        msg+=ret.stdout.decode()+"\n"
        msg+="STDERR: "
        msg+=ret.stderr.decode()+"\n"
        raise self.ProcessExitWithErrorsException(msg)

    # djvm

    def _djvm_insert(self,doc,page,pagenum=None):
        if not os.path.isfile(doc):
            shutil.copy(page, doc)
            return
        cmd=['djvm', '-i', doc, page]
        if pagenum is not None: cmd.append(str(pagenum))
        self._exec(cmd)


    ###############

    def _clean_infile(self,infile,dpi): return infile

    def _cleanup(self):
        for f in self._temporary_files:
            if os.path.isfile(f): os.remove(f)
            self._temporary_files.remove(f)

    def _action(self,infile,outfile,dpi): pass

    def single(self, infile, outfile, dpi):
        infile=self._clean_infile(infile,dpi)
        self._action(infile,outfile,dpi)
        # Check that the outfile has been created.
        if not os.path.isfile(outfile):
            msg = 'err: No encode errors, but "{0}" does not exist!'.format(outfile)
            print(msg, file=sys.stderr)
        self._cleanup()

    def __call__(self,book,outfile): 
        tempfile="temp.djvu"
        for page in book.pages:
            if self.bitonal != page.bitonal: continue
            page_number = book.pages.index(page) + 1
            print("A",page_number,page.path)
            self.single(page.path, tempfile, page.dpi)
            outfile.insert(tempfile)
            os.remove(tempfile)

class MinidjvuEncoder(ExternalEncoder):
    """
    Encode files with minidjvu.
    N.B., minidjvu is the only encoder function that expects a list a filenames
    and not a string with a single filename.  This is because minidjvu gains
    better compression with a shared dictionary across multiple images.
    """

    def single(self, infile, outfile, dpi): pass

    def __call__(self,book,outfile):
        def chunks(L,n):
            for i in range(0,len(L),n): 
                yield L[i:i+n]

        tempfile="temp.djvu"
        bitonals = []
        for page in book.pages:
            if page.bitonal:
                bitonals.append(page.path)
        if not bitonals: return

        for sublist in chunks(bitonals,100):
            self._minidjvu(sublist, outfile, book.dpi)
            self._cleanup()

    def _minidjvu(self, infiles, outfile, dpi):
        process_files = []
        for filename in infiles:
            extension = filename.split('.')[-1].lower()
            if extension in ['tif','tiff','pbm','pnm']:
                process_files.append(filename)
                continue
            converted=".".join(filename.split('.')[:-1])+".pbm"
            self._convert("PBM",filename,converted)
            self._temporary_files.append(converted)
            process_files.append(converted)

        tempfile = 'enc_temp.djvu'
        self._temporary_files.append(tempfile)

        base_cmd=['minidjvu', '-d', str(dpi) ] + self._options + process_files + [ tempfile ]
        self._exec(cmd)
        outfile.insert(tempfile)

class C44Encoder(ExternalEncoder):

    def _clean_infile(self,infile,dpi):
        extension = infile.split('.')[-1]
        if extension in ['pgm', 'ppm', 'jpg', 'jpeg']: return infile
        self._convert("PPM",infile,"temp.ppm")
        self._temporary_files.append("temp.ppm")
        return "temp.ppm"

    def _action(self,infile,outfile,dpi):
        cmd =[ 'c44','-dpi',str(dpi) ] + self._options + [ infile, outfile ] 
        self._exec(cmd)
        
class Cjb2Encoder(ExternalEncoder):
    bitonal = True

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

        cmd=["cjb2"]
        if (dpi > 25) and (dpi < 1200):
            cmd+=["-dpi",str(dpi)]
        cmd+=self._options
        cmd+=[ infile, outfile ]
        self._exec(cmd)

class CpaldjvuEncoder(ExternalEncoder):
    def _clean_infile(self,infile,dpi):
        extension = infile.split('.')[-1]
        if extension in ['ppm']: return infile
        self._convert("PPM",infile,"temp.ppm")
        self._temporary_files.append("temp.ppm")
        return "temp.ppm"

    def _action(self,infile,outfile,dpi):
        cmd =[ 'cpaldjvu','-dpi',str(dpi) ] + self._options + [ infile, outfile ] 
        self._exec(cmd)

class CsepdjvuEncoder(ExternalEncoder):
    def __init__(self,options,cjb2_options):
        ExternalEncoder.__init__(self,options)
        self._cjb2_options=shlex.split(cjb2_options)

    def _clean_infile(self,infile,dpi):
        # Separate the bitonal text (scantailor's mixed mode) from everything else.
        self._extract_graphics("PPM",infile,"temp_graphics.ppm")
        self._extract_textual("PBM",infile,"temp_textual.pbm")

        cmd=["cjb2"]
        if (dpi > 25) and (dpi < 1200):
            cmd+=["-dpi",str(dpi)]
        cmd+=self._options
        cmd+=[ 'temp_textual.pbm', 'enc_bitonal_out.djvu' ]

        self._exec(cmd)

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
        cmd=['csepdjvu', '-d', str(dpi)]+ self._options+[ "temp_merge.mix", "temp_final.djvu"]
        self._exec(cmd)
        DjvuFile(outfile).insert("temp_final.djvu") 
        #self._djvm_insert(outfile,"temp_final.djvu")  # QUI
        self._temporary_files.append("temp_final.djvu")

class Encoder:
    """
    An intelligent djvu super-encoder that can work with numerous djvu encoders.
    """

    def __init__(self, opts):
        self.opts = opts

        print(self.opts)

        self._minidjvu=MinidjvuEncoder(self.opts['cpaldjvu_options'])
        self._cjb2=Cjb2Encoder(self.opts['cjb2_options'])

        self._c44=C44Encoder(self.opts['c44_options'])
        self._cpaldjvu=CpaldjvuEncoder(self.opts['cpaldjvu_options'])
        self._csepdjvu=CsepdjvuEncoder(self.opts['csepdjvu_options'],self.opts["cjb2_options"])

        if self.opts["bitonal_encoder"]=="minidjvu":
            self._bitonal=self._minidjvu
        else:
            self._bitonal=self._cjb2

        if self.opts["color_encoder"]=="c44":
            self._color=self._c44
        if self.opts["color_encoder"]=="cpaldjvu":
            self._color=self._cpaldjvu
        else:
            self._color=self._csepdjvu

    def enc_book(self, book, outfile):
        """
        Encode pages, metadata, etc. contained within a organizer.Book() class.
        """

        outfile=DjvuFile(outfile)

        self._bitonal(book,outfile)
        self._color(book,outfile)

        # Add ocr data
        if self.opts['ocr']:
            for page in book.pages:
                handle = open('ocr.txt', 'w', encoding="utf8")
                handle.write(page.text)
                handle.close()
                page_number = book.pages.index(page) + 1
                outfile.add_text("ocr.txt",page_number)
                os.remove('ocr.txt')

        tempfile = 'temp.djvu'

        # Cover, metadata, bookmarks

        if book.cover_front is not None:
            self._c44.single(book.cover_front.path, tempfile, book.cover_front.dpi)
            outfile.add_cover_front(tempfile)

        if book.cover_back is not None:
            self._c44.single(book.cover_back.path, tempfile, book.cover_back.dpi)
            outfile.add_cover_back(tempfile)

        if book.suppliments['metadata'] is not None:
            outfile.add_metadata(book.suppliments['metadata'])

        if book.suppliments['bookmarks'] is not None:
            outfile.add_bookmarks(book.suppliments['bookmarks'])

        # Page numbering

        desc=[]
        index = 1
        if book.cover_front is not None:
            index = index + 1
        for page in book.pages:
            if page.title is None:
                index = index + 1
                continue
            desc.append( (index,page.title) )
            index = index + 1

        outfile.add_pages_number(desc)
        outfile.set_thumbnails(128)

        if os.path.isfile(tempfile):
            os.remove(tempfile)

        return None
