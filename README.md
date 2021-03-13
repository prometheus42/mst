
# MuseScoreTools

MuseScoreTools is a simple GUI tool to work convert and merge MuseScore files.

# Building standalone applications

To create a single EXE file for Windows user, a pyinstaller .spec file has to be created:

    pyinstaller --onefile --windowed -i images/icon.ico src\gui.py

Alternativly, you can use the provided spec file in the repo:

    pyinstaller mst_gui.spec 

# File list

* META-INF/manifest.xml -> manifest declaring all parts of the extension
* description.xml -> XML file with all information about the extension
* gui.xcu -> XML file for all GUI elements of the extension
* src/import_ical.py -> python code to read iCalendar file and write data into worksheet
* registration/license_*.txt -> license files in various languages
* description/description_*.txt -> info text for extension in various languages
* images/icon.png -> icon for extension
* extensionname.txt -> contains the name of the extension for build script
* build.py -> python script to build .oxt file

# Contributions

* Official MuseScore icon.

# License

This extension is released under the MIT License.

# Requirements

MST runs under Python 3.6 and newer.

The following Python packages are necessary:

* 
