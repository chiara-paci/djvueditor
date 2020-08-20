#! /usr/bin/env python3

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
Perform OCR operations using various engines.
"""

import difflib
import os
import re
import shutil
import subprocess
import sys

from html.parser import HTMLParser

from djvubind import utils

class BoundingBox(object):
    """
    A rectangular portion of an image that contains something of value, such as
    text or a collection of smaller bounding boxes.

        Attributes:
            * perimeter (dictionary): xmax, xmin, ymax, ymin - integer values for the coordinates of the box.
            * children (list): Either other bounding boxes or single character strings of each letter in the word.
    """

    def __init__(self):
        self.perimeter = {'xmax':0, 'xmin':1000000000, 'ymax':0, 'ymin':1000000000}
        self.children = []

    def add_element(self, box):
        """
        Adds a smaller BoundingBox.

            Arguments:
                * box (BoundingBox):
        """

        if box.perimeter['xmin'] < self.perimeter['xmin']:
            self.perimeter['xmin'] = box.perimeter['xmin']
        if box.perimeter['ymin'] < self.perimeter['ymin']:
            self.perimeter['ymin'] = box.perimeter['ymin']
        if box.perimeter['xmax'] > self.perimeter['xmax']:
            self.perimeter['xmax'] = box.perimeter['xmax']
        if box.perimeter['ymax'] > self.perimeter['ymax']:
            self.perimeter['ymax'] = box.perimeter['ymax']
        self.children.append(box)

    def sanity_check(self):
        """
        Verifies that the x/y min values are not greater than the x/y max values.

            Raises:
                * ValueError: A min is greater than a max.  Either there was bad input nothing was added to the bounding box.
        """

        if (self.perimeter['xmin'] > self.perimeter['xmax']) or (self.perimeter['ymin'] > self.perimeter['ymax']):
            raise ValueError('Boxing information is impossible (x/y min exceed x/y max).')
        return None


class djvuWordBox(BoundingBox):
    """
    BoundingBox of a single word.  See :py:meth:`~djvubind.ocr.BoundingBox`
    """

    def add_character(self, boxing):
        """
        Adds a character to the BoundingBox.

            Arguments:
                * boxing (dictionary): char, xmax, xmin, ymax, ymin.
        """

        if boxing['xmin'] < self.perimeter['xmin']:
            self.perimeter['xmin'] = boxing['xmin']
        if boxing['ymin'] < self.perimeter['ymin']:
            self.perimeter['ymin'] = boxing['ymin']
        if boxing['xmax'] > self.perimeter['xmax']:
            self.perimeter['xmax'] = boxing['xmax']
        if boxing['ymax'] > self.perimeter['ymax']:
            self.perimeter['ymax'] = boxing['ymax']
        self.children.append(boxing['char'])

    def encode(self):
        self.sanity_check()
        return '(word {0} {1} {2} {3} "{4}")'.format(self.perimeter['xmin'], self.perimeter['ymin'], self.perimeter['xmax'], self.perimeter['ymax'], ''.join(self.children))

class djvuLineBox(BoundingBox):
    """
    BoundingBox of a single line.  See :py:meth:`~djvubind.ocr.BoundingBox`
    """

    def encode(self):
        # This is a hackish solution for when a line happens to be blank (only cuneiform hocr?).
        # Something here with BoundingBox needs to be thought through better.
        if (self.perimeter['xmin'] == 1000000000) and (self.perimeter['ymin'] == 1000000000):
            return ''
        self.sanity_check()
        line = '(line {0} {1} {2} {3}'.format(self.perimeter['xmin'], self.perimeter['ymin'], self.perimeter['xmax'], self.perimeter['ymax'])
        words = '\n    '.join([x.encode() for x in self.children])
        return line+'\n    '+words+')'


class djvuPageBox(BoundingBox):
    """
    BoundingBox of a single page.  See :py:meth:`~djvubind.ocr.BoundingBox`
    """

    def encode(self):
        self.sanity_check()
        page = '(page {0} {1} {2} {3}'.format(self.perimeter['xmin'], self.perimeter['ymin'], self.perimeter['xmax'], self.perimeter['ymax'])
        lines = '\n  '.join([x.encode() for x in self.children])
        return page+'\n  '+lines+')'

class TesseractParser(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
        self.boxing = []
        self.version = 'tesseract'
        self.data = ''

    def parse(self, data):
        self.data = data
        self.feed(data)

    def handle_starttag(self, tag, attrs):
        if (tag == 'br') or (tag == 'p'):
            if (len(self.boxing) > 0):
                self.boxing.append('newline')
            return
        if tag != "span": return
        if not (('class', 'ocrx_word') in attrs): return
        #elif (tag == 'span') and (('class', 'ocrx_word') in attrs):
        # Get the whole element, not just the tag.
        element = {}
        element['complete'] = re.search('{0}(.*?)</span>'.format(self.get_starttag_text()), self.data).group(0)
        element['text'] = re.search('\'>(.*?)</span', element['complete']).group(1)
        element['text'] = re.sub('<[\w\/\.]*>', '', element['text'])
        element['text'] = utils.replace_html_codes(element['text'])
        element['positions'] = re.search('bbox ([0-9\s]*)', element['complete']).group(1)
        element['positions'] = [int(item) for item in element['positions'].split()]

        i = 0
        for char in element['text']:
            if element['positions'][i:i+4] == []:
                continue
            section = element['positions'][i:i+4]
            positions = {'char':char, 'xmin':section[0], 'ymin':section[1], 'xmax':section[2], 'ymax':section[3]}
            #i = i+4

            # A word break is indicated by a space (go figure).
            if (char == ' '):
                self.boxing.append('space')
                continue

            # Escape special characters
            subst = {'"': '\\"', "'":"\\'", '\\': '\\\\'}
            if positions['char'] in subst.keys():
                positions['char'] = subst[positions['char']]
            self.boxing.append(positions)

        self.boxing.append('space')

class Tesseract(object):
    """
    Everything needed to work with the Tesseract OCR engine.
    """

    def __init__(self, options):
        if not utils.is_executable('tesseract'):
            raise OSError('Tesseract is either not installed or not in the configured path.')

        sub = subprocess.Popen('tesseract --version', shell=True, 
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
        sub.wait()
        #version = str(sub.stderr.read())
        version = str(sub.stdout.read())

        version = version.split('\\n')[0]
        version = version.split()[-1]
        version = version.split('.')[0]

        self.version = int(version)
        self.options = options

    def _correct_boxfile(self, boxdata, text):
        """
        Reconciles Tesseract's boxfile data with it's plain text data.

        The Tesseract boxfile does not include information like spacing, which is kinda important
        since we want to know where one word ends and the next begins.  The plain textfile will
        give that information, but sometimes its content does not exactly match the boxfile.  So we
        do our best to merge those two pieces of data together and "fix" the boxfile to match the
        textfile.
        """

        # Convert the boxing information into a plain text string with no bounding information.
        boxtext = ''
        for entry in boxdata:
            boxtext = boxtext + entry['char']
        # Remove spacing and newlines from the readable text because the boxing data doesn't have those.
        text = text.replace(' ', '')
        text = text.replace('\n', '')

        # Figure out what changes are needed, but don't do them immediately since it would
        # change the boxdata index and screw up the next action.
        diff = difflib.SequenceMatcher(None, boxtext, text)
        queu = []
        for action, a_start, a_end, b_start, b_end in diff.get_opcodes():
            entry = boxdata[a_start]
            item = {'action':action, 'target':entry, 'boxtext':boxtext[a_start:a_end], 'text':text[b_start:b_end]}
            queu.append(item)

        # Make necessary changes
        for change in queu:
            if (change['action'] == 'replace'):
                if (len(change['boxtext']) == 1) and (len(change['text']) == 1):
                    index = boxdata.index(change['target'])
                    boxdata[index]['char'] = change['text']
                elif (len(change['boxtext']) > 1) and (len(change['text']) == 1):
                    # Combine the boxing data
                    index = boxdata.index(change['target'])
                    new = {'char':'', 'xmin':0, 'ymin':0, 'xmax':0, 'ymax':0}
                    new['char'] = change['text']
                    new['xmin'] = min([x['xmin'] for x in boxdata[index:index+len(change['boxtext'])]])
                    new['ymin'] = min([x['ymin'] for x in boxdata[index:index+len(change['boxtext'])]])
                    new['xmax'] = min([x['xmax'] for x in boxdata[index:index+len(change['boxtext'])]])
                    new['ymax'] = min([x['ymax'] for x in boxdata[index:index+len(change['boxtext'])]])
                    del(boxdata[index:index+len(change['boxtext'])])
                    boxdata.insert(index, new)
                elif (len(change['boxtext']) == 1) and (len(change['text']) > 1):
                    # Use the same boxing data.  Will djvused complain that character
                    # boxes overlap?
                    index = boxdata.index(change['target'])
                    del(boxdata[index])
                    i = 0
                    for char in list(change['text']):
                        new = {'char':char, 'xmin':change['target']['xmin'], 'ymin':change['target']['ymin'], 'xmax':change['target']['xmax'], 'ymax':change['target']['ymax']}
                        boxdata.insert(index+i, new)
                        i = i + 1
                elif (len(change['boxtext']) > 1) and (len(change['text']) > 1):
                    if (len(change['boxtext']) == len(change['text'])):
                        index = boxdata.index(change['target'])
                        for char in list(change['text']):
                            boxdata[index]['char'] = char
                            index = index + 1
                    else:
                        # Delete the boxdata and replace with the plain text data
                        index = boxdata.index(change['target'])
                        deletions = boxdata[index:index+len(change['boxtext'])]
                        for target in deletions:
                            boxdata.remove(target)

                        i = 0
                        for char in list(change['text']):
                            new = {'char':char, 'xmin':change['target']['xmin'], 'ymin':change['target']['ymin'], 'xmax':change['target']['xmax'], 'ymax':change['target']['ymax']}
                            boxdata.insert(index+i, new)
                            i = i + 1
            elif (change['action'] == 'delete'):
                index = boxdata.index(change['target'])
                deletions = boxdata[index:index+len(change['boxtext'])]
                for target in deletions:
                    boxdata.remove(target)
            elif (change['action'] == 'insert'):
                # *Don't* use the boundaries of previous and next characters to guess at a boundary
                # box.  Things would be ugly if the next character happened to be on a new line.
                # Just duplicate the boundaries of the previous character
                index = boxdata.index(change['target'])
                i = 0
                for char in list(change['text']):
                    new = {'char':char, 'xmin':change['target']['xmin'], 'ymin':change['target']['ymin'], 'xmax':change['target']['xmax'], 'ymax':change['target']['ymax']}
                    boxdata.insert(index+i, new)
                    i = i + 1

        return boxdata

    def analyze(self, page):
        """
        Performs OCR analysis on the image and returns a djvuPageBox object.
        """
        filename=page.path

        #if self.version >= 3:
        #basename = os.path.split(filename)[1].split('.')[0]
        basename=page.basepath
        tesseractpath = utils.get_executable_path('tesseract')

        if not os.path.exists(basename+".hocr"):
            utils.execute('{0} "{1}" "{2}" {3} hocr'.format(tesseractpath, filename, basename, self.options))

        with open('{0}.hocr'.format(basename), 'r') as handle:
            text = handle.read()

        # Clean up excess files.
        #os.remove(basename+'.hocr')

        parser = TesseractParser()
        parser.parse(text)

        # hocr inverts the y-axis compared to what djvu expects.  The total height of the
        # image is needed to invert the values.
        #height = int(utils.execute('identify -format %H "{0}"'.format(filename), capture=True))
        height=page.height

        for entry in parser.boxing:
            if entry not in ['space', 'newline']:
                ymin, ymax = entry['ymin'], entry['ymax']
                entry['ymin'] = height - ymax
                entry['ymax'] = height - ymin

        return parser.boxing


def translate(boxing):
    """
    Translate djvubind's internal boxing information into a djvused format.

    .. warning::
       This function will eventually migrate to djvubind.encode
    """

    page = djvuPageBox()
    line = djvuLineBox()
    word = djvuWordBox()
    for entry in boxing:
        if entry == 'newline':
            if (word.children != []):
                line.add_element(word)
            page.add_element(line)
            line = djvuLineBox()
            word = djvuWordBox()
        elif entry == 'space':
            if (word.children != []):
                line.add_element(word)
            word = djvuWordBox()
        else:
            word.add_character(entry)

    if (word.children != []):
        line.add_element(word)
    if (line.children != []):
        page.add_element(line)

    if (page.children != []):
        return page.encode()

    return ''
