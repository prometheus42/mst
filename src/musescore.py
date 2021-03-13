import zipfile
import xml.etree.ElementTree as ET
import os
import sys
import shutil
import tempfile


class CapellaFile(object):
    pass
    # TODO: Convert to MuseScore including fixes
    # TODO: Check file for correct timing


class MuseScoreException(Exception):
    pass


class MuseScoreFile(object):
    def __init__(self, filepath):
        self.filepath = filepath
        _, ext = os.path.splitext(filepath)
        if ext == '.mscx':
            self.tree = MuseScoreFile.load_xml_file(filepath)
        elif ext == '.mscz':
            self.tree = MuseScoreFile.load_zip_file(filepath)
        else:
            raise('invalid MuseScore file')


    def get_staff_element(self):
        staff = self.tree.getroot().findall('Score/Staff')
        if len(staff) != 1:
            raise MuseScoreException('too many staffs (main)')
        return staff[0]


    def get_staff_content(self):
        staff = self.tree.getroot().findall('Score/Staff')
        if len(staff) != 1:
            raise MuseScoreException('too many staffs (content)')
        return self.tree.getroot().findall('Score/Staff/*')


    def remove_clefs(self):
        clef_parents = self.tree.getroot().findall('Score/Staff/Measure/voice/Clef/..')
        for parent in clef_parents:
            clef = parent.find('Clef')
            parent.remove(clef)


    def remove_newlines(self):
        measures = self.tree.getroot().findall('''Score/Staff/Measure/LayoutBreak/subtype/[.='line']/../..''')
        for measure in measures:
            newline = measure.find('LayoutBreak')
            measure.remove(newline)


    def add_sectionbreak(self):
        # find last measure
        lastmeasure = self.tree.getroot().findall('Score/Staff/Measure[last()]')
        lastmeasure = lastmeasure[0]

        # check if section break exists
        sectionbreak = lastmeasure.find('''LayoutBreak/subtype/[.='section']''')
        if sectionbreak:
            return
        
        # add section break
        layoutbreak = ET.SubElement(lastmeasure, 'LayoutBreak')
        subtype = ET.SubElement(layoutbreak, 'subtype')
        subtype.text = 'section'


    def set_text_as_title(self):
        # find target title text
        texts = self.tree.getroot().findall('Score/Staff/Measure/voice/StaffText/text')
        if len(texts) != 1:
            # TODO: get warning to gui
            print('set_text_as_title failed - too many texts')
            return
        title = texts[0].text

        # find vboxs
        vboxs = self.tree.getroot().findall('Score/Staff/VBox')
        if len(vboxs) > 1:
            # TODO: get warning to gui
            print('set_text_as_title failed - too many vboxs')
            return
        elif len(vboxs) == 0:
            staff = self.tree.getroot().findall('Score/Staff')
            vbox = ET.Element('VBox')
            height = ET.SubElement(vbox, 'height')
            height.text = '4'
            staff.insert(vbox)
        else:
            vbox = vboxs[0]

        # add title to vbox
        subtitles = vbox.findall('''Text/style/[.='Subtitle']/..''')
        if len(subtitles) == 1:
            subtitles[0].find('text').text = title
        elif len(subtitles) == 0:
            textel = ET.SubElement(vbox, 'Text')
            style = ET.SubElement(textel, 'style')
            style.text = 'Subtitle'
            text = ET.SubElement(textel, 'text')
            text.text = title
        else:
            # TODO: get warning to gui
            print('set_text_as_title failed - too many subtitles')
            return

        # remove text
        stafftext = self.tree.getroot().findall('Score/Staff/Measure/voice/StaffText/text/..')[0]
        voice = self.tree.getroot().findall('Score/Staff/Measure/voice/StaffText/text/../..')[0]
        voice.remove(stafftext)
        

    def write(self, outpath):
        _, ext = os.path.splitext(outpath)
        if ext == '.mscx':
            self.tree.write(outpath, encoding='utf8')
        elif ext == '.mscz':
            with tempfile.TemporaryDirectory() as tempdir:
                # determine paths
                scorepath = os.path.join(tempdir, 'score.mscx')
                metapath = os.path.join(tempdir, 'META-INF/')
                containerpath = os.path.join(tempdir, 'META-INF/container.xml')

                # save score
                self.tree.write(scorepath, encoding='utf8')

                # create meta dir
                os.mkdir(metapath)

                # create container info
                croot = ET.Element('container')
                crootfiles = ET.SubElement(croot, 'rootfiles')
                crootfile = ET.SubElement(crootfiles, 'rootfile', attrib={'full-path': 'score.mscx'})
                ctree = ET.ElementTree(croot)
                ctree.write(containerpath, encoding='utf8')

                # zip dir
                with zipfile.ZipFile(outpath, 'w', zipfile.ZIP_DEFLATED) as fd:
                    for root, dirs, files in os.walk(tempdir):
                        for file in files:
                            dst_path = os.path.join(root, file)
                            arc_path = os.path.relpath(dst_path, tempdir)
                            fd.write(dst_path, arc_path)


    @staticmethod
    def load_zip_file(filepath):
        with zipfile.ZipFile(filepath, 'r') as archive:
            with archive.open('META-INF/container.xml') as fd:
                parser = ET.XMLParser(encoding='utf-8')
                rootfiles = ET.parse(fd, parser=parser).getroot().findall('rootfiles/rootfile')
                if len(rootfiles) != 1:
                    raise Exception('too many rootfiles')
                rootfile = rootfiles[0].get('full-path')
            
            with archive.open(rootfile) as fd:
                parser = ET.XMLParser(encoding='utf-8')
                tree = ET.parse(fd, parser=parser)
        return tree


    @staticmethod
    def load_xml_file(filepath):
        with open(filepath, encoding='utf8') as fd:
            parser = ET.XMLParser(encoding='utf-8')
            tree = ET.parse(fd, parser=parser)
        return tree


    @staticmethod
    def merge_files(mainfile, contentfiles, output):
        # load mainfile
        if not isinstance(mainfile, MuseScoreFile):
            mainfile = MuseScoreFile(mainfile)
        mainstaff = mainfile.get_staff_element()
        maincontent = mainfile.get_staff_content()

        # remove content from mainfile
        for e in maincontent:
            mainstaff.remove(e)
        
        # add content from contentfiles
        for f in contentfiles:
            if not isinstance(f, MuseScoreFile):
                f = MuseScoreFile(f)
            mainstaff.extend(f.get_staff_content())

        # write file to output
        mainfile.write(output)


def merge_files(files, output_file):
    msf = []
    for f in files:
        msf.append(MuseScoreFile(f))
    MuseScoreFile.merge_files(msf[0], msf, output_file)


def convert_files(files, copy_titles=False, remove_newlines=False, remove_clefs=False, add_section_break=False):
    for f in files:
        # load file
        msf = MuseScoreFile(f)

        # convert file
        if copy_titles:
            msf.set_text_as_title()
        if remove_newlines:
            msf.remove_newlines()
        if remove_clefs:
            msf.remove_clefs()
        if add_section_break:
            msf.add_sectionbreak()

        # create backup
        shutil.copy(f, f + '~')

        # write file
        msf.write(f)
