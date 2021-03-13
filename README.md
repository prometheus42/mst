
# MuseScoreTools

MuseScoreTools is a simple GUI tool to work convert and merge MuseScore files.

# Building standalone applications

To create a single EXE file for Windows user, a pyinstaller .spec file has to be created:

    pyinstaller --clean --onefile --windowed -n MuseScoreTools -i images/mscore3.ico src\gui.py


# Contributions

* Official MuseScore icon.

# License

This extension is released under the MIT License.

# Requirements

MST runs under Python 3.6 and newer.

The following Python packages are necessary:

* 
