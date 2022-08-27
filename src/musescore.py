
import os
import sys
import copy
import uuid
import shutil
import zipfile
import tempfile
import xml.etree.ElementTree as ET


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
            raise MuseScoreException('invalid MuseScore file')


    @staticmethod
    def _get_staff_element_from_tree(tree):
        staff = tree.getroot().findall('Score/Staff')
        if len(staff) != 1:
            raise MuseScoreException('too many staffs (main)')
        return staff[0]

    @staticmethod
    def _get_staff_content_from_tree(tree):
        staff = tree.getroot().findall('Score/Staff')
        if len(staff) != 1:
            raise MuseScoreException('too many staffs (content)')
        return tree.getroot().findall('Score/Staff/*')


    def get_staff_element(self):
        return MuseScoreFile._get_staff_element_from_tree(self.tree)


    def get_staff_content(self):
        return MuseScoreFile._get_staff_content_from_tree(self.tree)


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
            staff = self.tree.getroot().findall('Score/Staff')[0]
            vbox = ET.Element('VBox')
            height = ET.SubElement(vbox, 'height')
            height.text = '4'
            staff.insert(0, vbox)
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


    def contains_time_sig(self):
        time_sig = self.tree.getroot().findall('Score/Staff/Measure/voice/TimeSig')
        if time_sig:
            return True
        else:
            return False


    def fix_key_sig(self):
        time_sig = self.tree.getroot().findall('Score/Staff/Measure[1]/voice/KeySig')
        if not time_sig:
            voice_root = self.tree.getroot().findall('Score/Staff/Measure[1]/voice')[0]
            key_sig = ET.Element('KeySig')
            accidental = ET.SubElement(key_sig, 'accidental')
            accidental.text = '0'
            voice_root.insert(0, key_sig)


    @staticmethod
    def _write_tree(tree, outpath):
        _, ext = os.path.splitext(outpath)
        if ext == '.mscx':
            tree.write(outpath, encoding='utf8')
        elif ext == '.mscz':
            with tempfile.TemporaryDirectory() as tempdir:
                # determine paths
                scorepath = os.path.join(tempdir, 'score.mscx')
                metapath = os.path.join(tempdir, 'META-INF/')
                containerpath = os.path.join(tempdir, 'META-INF/container.xml')

                # save score
                tree.write(scorepath, encoding='utf8')

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


    def write(self, outpath):
        self._write_tree(self.tree, outpath)


    def split(self, outdir):
        '''Splits a file at VBOX-Elements into multiple files.'''
        # copy tree as template for parts and remove content
        template = copy.deepcopy(self.tree)
        templatestaff = MuseScoreFile._get_staff_element_from_tree(template)
        templatecontent = MuseScoreFile._get_staff_content_from_tree(template)
        for e in templatecontent:
            templatestaff.remove(e)

        # extract part and create new copy of template
        parts = []
        content = self.get_staff_content()
        for e in content:
            if e.tag == 'VBox':
                # extract title and create new part
                titles = e.findall('''Text/style/[.='Title']/../text''')
                if len(titles) == 1:
                    title = titles[0].text
                elif len(titles) == 0:
                    title = 'unknown_title_{}'.format(len(parts) + 1)
                else:
                    print('error')      # TODO
                    title = 'unknown_title_{}'.format(len(parts) + 1)

                parts.append({'title': title, 'elements': []})

            # add element to current part
            parts[-1]['elements'].append(e)

        # output parts to different files
        for part in parts:
            part_tree = copy.deepcopy(template)
            part_staff = MuseScoreFile._get_staff_element_from_tree(part_tree)
            for e in part['elements']:
                part_staff.append(e)

            part_path = part['title']

            # Sanitize path a bit (complete sanitation is complex, so lets do that another time)
            part_path = part_path.replace('\n', ' ')
            part_path = part_path.replace('\r', '')
            part_path = part_path.replace('\t', ' ')
            part_path = part_path.replace('<', '')
            part_path = part_path.replace('>', '')
            part_path = part_path.replace(':', '')
            part_path = part_path.replace('"', '')
            part_path = part_path.replace('/', '')
            part_path = part_path.replace('\\', '')
            part_path = part_path.replace('|', '')
            part_path = part_path.replace('?', '')
            part_path = part_path.replace('*', '')

            part_path = os.path.join(outdir, part_path + '.mscz')

            # Change path if file already exists, to avoid overwriting files
            if os.path.isfile(part_path):
                part_path = os.path.join(outdir, part['title'] + '-' + uuid.uuid4().hex[:8] + '.mscz')

            MuseScoreFile._write_tree(part_tree, part_path)


    @staticmethod
    def load_zip_file(filepath):
        with zipfile.ZipFile(filepath, 'r') as archive:
            with archive.open('META-INF/container.xml') as fd:
                parser = ET.XMLParser(encoding='utf-8')
                try:
                    rootfiles = ET.parse(fd, parser=parser).getroot().findall('rootfiles/rootfile')
                except ET.ParseError as e:
                    raise MuseScoreException('Could not parse file: {}'.format(e))
                if len(rootfiles) != 1:
                    raise Exception('too many rootfiles')
                rootfile = rootfiles[0].get('full-path')

            with archive.open(rootfile) as fd:
                parser = ET.XMLParser(encoding='utf-8')
                try:
                    tree = ET.parse(fd, parser=parser)
                except ET.ParseError as e:
                    raise MuseScoreException('Could not parse file: {}'.format(e))
        return tree


    @staticmethod
    def load_xml_file(filepath):
        with open(filepath, encoding='utf8') as fd:
            parser = ET.XMLParser(encoding='utf-8')
            try:
                tree = ET.parse(fd, parser=parser)
            except ET.ParseError as e:
                raise MuseScoreException('Could not parse file: {}'.format(e))
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
    if len(files) == 0:
        raise MuseScoreException('merge without failes not possible')

    msf_main = MuseScoreFile(files[0])
    msf = []
    for f in files:
        msf.append(MuseScoreFile(f))
    MuseScoreFile.merge_files(msf_main, msf, output_file)


def convert_files(files, copy_titles=False, remove_newlines=False, remove_clefs=False, add_section_break=False, fix_key_sig=False):
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
        if fix_key_sig:
            msf.fix_key_sig()

        # create backup
        shutil.copy(f, f + '~')

        # write file
        msf.write(f)
