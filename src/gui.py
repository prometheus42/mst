#! /usr/bin/env python3

import sys
import logging
import logging.handlers
import tkinter as tk
import tkinter.messagebox as messagebox
from tkinter.ttk import Button, Label, Separator, Checkbutton
from tkinter.filedialog import askopenfilenames, asksaveasfilename, askopenfilename, askdirectory
import musescore


logger = logging.getLogger('mst_gui')

APP_NAME = 'MuseScoreTools'
LOG_FILENAME = 'mst_gui.log'
WIDTH = 600
HEIGHT = 400
PADX = 10
PADY = 5


def center(win):
    """
    Centers a tkinter window.

    :param win: the root or Toplevel window to center

    Source: https://stackoverflow.com/a/10018670
    """
    win.update_idletasks()
    width = win.winfo_width()
    frm_width = win.winfo_rootx() - win.winfo_x()
    win_width = width + 2 * frm_width
    height = win.winfo_height()
    titlebar_height = win.winfo_rooty() - win.winfo_y()
    win_height = height + titlebar_height + frm_width
    x = win.winfo_screenwidth() // 2 - win_width // 2
    y = win.winfo_screenheight() // 2 - win_height // 2
    win.geometry('{}x{}+{}+{}'.format(width, height, x, y))
    win.deiconify()


def create_logger():
    # create logger for this application
    global logger
    logger.setLevel(logging.DEBUG)
    log_to_file = logging.handlers.RotatingFileHandler(LOG_FILENAME, maxBytes=262144, backupCount=5, encoding='utf-8')
    log_to_file.setLevel(logging.DEBUG)
    logger.addHandler(log_to_file)
    log_to_screen = logging.StreamHandler(sys.stdout)
    log_to_screen.setLevel(logging.INFO)
    logger.addHandler(log_to_screen)


class FileListView(tk.Frame):
    def __init__(self, master=None):
        super().__init__(master)
        self.master = master
        self.create_widgets()

    def create_widgets(self):
        self.listbox = tk.Listbox(self, selectmode=tk.EXTENDED)
        self.listbox.pack(padx=PADX, pady=PADY, fill=tk.BOTH, expand=True)
        self.buttonframe = tk.Frame(self)
        add_button = Button(self.buttonframe, text='+', command=self.on_add_files)
        add_button.pack(side=tk.LEFT, padx=PADX, anchor=tk.W)
        remove_button = Button(self.buttonframe, text='-', command=self.on_remove_file)
        remove_button.pack(side=tk.LEFT, padx=PADX, anchor=tk.W)
        up_button = Button(self.buttonframe, text='⏶', command=lambda: self.on_move_file(-1))
        up_button.pack(side=tk.LEFT, padx=PADX, anchor=tk.W)
        down_button = Button(self.buttonframe, text='⏷', command=lambda: self.on_move_file(1))
        down_button.pack(side=tk.LEFT, padx=PADX, anchor=tk.W)
        remove_all_button = Button(self.buttonframe, text='x', command=self.on_remove_all_files)
        remove_all_button.pack(side=tk.RIGHT, padx=PADX, anchor=tk.E)
        self.buttonframe.pack(padx=PADX, pady=PADY, fill=tk.X)

    def on_remove_all_files(self):
        self.listbox.delete(0, tk.END)

    def on_add_files(self):
        filenames = askopenfilenames(initialdir='.', title = 'MuseScore-Dateien auswählen...',
                                     filetypes =(('MuseScore-Dateien', '*.mscx, *.mscz'),('Alle Dateien','*.*')))
        logger.info('Chosen files: {}'.format(filenames))
        if type(filenames) == tuple:
            for f in filenames:
                self.listbox.insert(tk.END, f)
        else:
            self.listbox.insert(tk.END, filenames)

    def on_remove_file(self):
        selected_files = self.listbox.curselection()
        if selected_files:
            for i in selected_files:
                self.listbox.delete(i)

    def on_move_file(self, direction):
        """
        Moves item in Listbox up (direction = -1) or down (direction = 1).
        """
        # Source: https://stackoverflow.com/a/52763936
        selected_files = self.listbox.curselection()
        if not selected_files:
            return
        for f in selected_files:
            if direction == -1 and f == 0:
                continue
            if direction == 1 and f == len(self.listbox.get(0, tk.END)) - 1:
                continue
            text = self.listbox.get(f)
            self.listbox.delete(f)
            self.listbox.insert(f + direction, text)
            self.listbox.selection_set(f + direction)

    def on_move_file_down(self):
        if self.listbox.curselection:
            pass

    def get_file_list(self):
        return self.listbox.get(0, tk.END)


class MainWindow(tk.Frame):
    def __init__(self, master=None):
        super().__init__(master)
        self.master = master
        self.output_file = ''
        self.split_input_file = ''
        self.split_output_dir = ''
        master.title(APP_NAME)
        master.minsize(WIDTH, HEIGHT)
        # master.geometry('{}x{}'.format(WIDTH, HEIGHT))
        # photo = tk.PhotoImage(file='./images/mscore3.png')
        # master.iconphoto(False, photo)
        # center(window)
        self.pack()
        nb = tk.ttk.Notebook(root)
        nb.pack(padx=PADX, pady=PADY, fill=tk.BOTH, expand=True)
        nb.add(self.create_convert_widgets(nb), text='Konvertieren...')
        nb.add(self.create_merge_widgets(nb), text='Zusammenführen...')
        nb.add(self.create_split_widgets(nb), text='Aufteilen...')
        nb.enable_traversal()

    def create_convert_widgets(self, notebook):
        frame = tk.Frame(notebook)
        self.convert_file_list = FileListView(frame)
        self.convert_file_list.pack(padx=0, pady=0, fill=tk.BOTH, expand=True)
        self.copy_titles = tk.IntVar()
        copy_titles_checkbox = Checkbutton(frame, text='Titel kopieren', variable=self.copy_titles)
        copy_titles_checkbox.pack(padx=PADX, pady=PADY, anchor=tk.W)
        self.remove_newline = tk.IntVar()
        remove_newline_checkbox = Checkbutton(frame, text='Zeilenumbrüche entfernen', variable=self.remove_newline)
        remove_newline_checkbox.pack(padx=PADX, pady=PADY, anchor=tk.W)
        self.remove_clefs = tk.IntVar()
        remove_clefs_checkbox = Checkbutton(frame, text='Notenschlüssel entfernen', variable=self.remove_clefs)
        remove_clefs_checkbox.pack(padx=PADX, pady=PADY, anchor=tk.W)
        self.add_section_break = tk.IntVar()
        add_section_break_checkbox = Checkbutton(frame, text='Abschnittsumrüche einfügen', variable=self.add_section_break)
        add_section_break_checkbox.pack(padx=PADX, pady=PADY, anchor=tk.W)
        convert_button = Button(frame, text='Konvertieren...', command=self.on_convert)
        convert_button.pack(padx=PADX, pady=PADY)
        return frame

    def create_merge_widgets(self, notebook):
        frame = tk.Frame(notebook)
        self.merge_file_list_view = FileListView(frame)
        self.merge_file_list_view.pack(padx=0, pady=0, fill=tk.BOTH, expand=True)
        output_file_button = Button(frame, text='Ausgabedatei auswählen...', command=self.on_choose_output_file)
        output_file_button.pack(padx=PADX, pady=PADY, anchor=tk.W)
        self.output_file_label = Label(frame, text='', font=('Courier', 10))
        self.output_file_label.pack(padx=PADX, pady=PADY, anchor=tk.W)
        merge_button = Button(frame, text='Zusammenführen...', command=self.on_merge)
        merge_button.pack(padx=PADX, pady=PADY)
        return frame

    def create_split_widgets(self, notebook):
        frame = tk.Frame(notebook)
        input_file_button = Button(frame, text='Eingabedatei auswählen...', command=self.on_choose_input_file)
        input_file_button.pack(padx=PADX, pady=PADY, anchor=tk.W)
        self.split_input_file_label = Label(frame, text='', font=('Courier', 10))
        self.split_input_file_label.pack(padx=PADX, pady=PADY, anchor=tk.W)
        split_output_directory_button = Button(frame, text='Ausgabeverzeichnis auswählen...', command=self.on_choose_output_dir)
        split_output_directory_button.pack(padx=PADX, pady=PADY, anchor=tk.W)
        self.split_output_directory_label = Label(frame, text='', font=('Courier', 10))
        self.split_output_directory_label.pack(padx=PADX, pady=PADY, anchor=tk.W)
        split_button = Button(frame, text='Aufteilen...', command=self.on_split)
        split_button.pack(padx=PADX, pady=PADY)
        return frame

    def on_choose_output_file(self):
        filename = asksaveasfilename(initialdir='.', title = 'Ausgabedatei auswählen...',
                                     filetypes =(('MuseScore-Dateien', '*.mscx, *.mscz'),('Alle Dateien','*.*')))
        if filename:
            self.output_file = filename
            self.output_file_label['text'] = filename

    def on_choose_input_file(self):
        filename = askopenfilename(initialdir='.', title = 'Eingabedatei auswählen...',
                                   filetypes =(('MuseScore-Dateien', '*.mscx, *.mscz'),('Alle Dateien','*.*')))
        if filename:
            self.split_input_file = filename
            self.split_input_file_label['text'] = filename

    def on_choose_output_dir(self):
        dir = askdirectory(initialdir='.', title = 'Ausgabeverzeichnis auswählen...')
        if dir:
            self.split_output_dir = dir
            self.split_output_directory_label['text'] = dir

    def on_merge(self):
        if self.output_file:
            files = self.merge_file_list_view.get_file_list()
            if files:
                logging.info('Merging files ({}) to output file: {}.'.format(files, self.output_file))
                musescore.merge_files(files, self.output_file)
            else:
                logging.error('No input files for merging chosen!')
                messagebox.showerror('Keine Eingabedateien ausgewählt', 'Es sind keine Eingabedateien ausgewählt.')
        else:
            logging.error('No output file chosen!')
            messagebox.showerror('Keine Ausgabedatei ausgewählt', 'Es ist keine Ausgabedatei ausgewählt.')

    def on_convert(self):
        files = self.convert_file_list.get_file_list()
        if files:
            logging.info('Converting files: {}'.format(files))
            musescore.convert_files(files,
                                          copy_titles=self.copy_titles.get(),
                                          remove_newlines=self.remove_newline.get(),
                                          remove_clefs=self.remove_clefs.get(),
                                          add_section_break=self.add_section_break.get())
        else:
            logging.error('No input files for converting chosen!')
            messagebox.showerror('Keine Eingabedateien ausgewählt', 'Es sind keine Eingabedateien ausgewählt.')

    def on_split(self):
        if self.split_output_dir:
            if self.split_input_file:
                logging.info('Splitting file ({}) to output dir: {}.'.format(self.split_input_file, self.split_output_dir))
                m = musescore.MuseScoreFile(self.split_input_file)
                m.split(self.split_output_dir)
            else:
                logging.error('No input file for splitting chosen!')
                messagebox.showerror('Kein Eingabedatei ausgewählt', 'Es ist kein Eingabedatei ausgewählt.')
        else:
            logging.error('No output directory chosen!')
            messagebox.showerror('Kein Ausgabeverzeichnis ausgewählt', 'Es ist kein Ausgabeverzeichnis ausgewählt.')


if __name__ == '__main__':
    create_logger()
    root = tk.Tk()
    root.wm_title(APP_NAME)
    app = MainWindow(master=root)
    logger.info('Starting GUI...')
    app.mainloop()
