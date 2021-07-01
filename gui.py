import tkinter as tk
from tkinter import filedialog,ttk,messagebox
from datetime import datetime
import os
import threading
import imageprocess as imgproc
from pathlib import Path

PIC_TYPE=(".JPG",".jpg")
today=datetime.today()
date=today.strftime("%d-%m_%H-%M")

def getFolderPath():

    #Display window with directory
    folder = filedialog.askdirectory(initialdir=initdir.get())

    try:
        directory.set(folder)
        initdir.set(folder)

        #Get amount of photos ion directory
        amount.set(len([photo for photo in os.listdir(folder) if photo.endswith(PIC_TYPE)]))
        #Set progress bar value
        progress_bar.config(maximum=amount.get())

        if directory.get()!="":
            #Reset progress bar if directory is empty
            progress_bar['value'] = 0
        
    except:
        if directory.get()!="":

            if os.path.exists(directory.get()):
                initdir.set(directory.get())
            
            else:
                initdir.set("C:/")
        else:
            initdir.set("C:/")

    #If path doesn't fit, view right side of the path
    entry_path.xview("end")    

def doAction():
    
    if entry_path.get()=="" and directory.get()=="":
        #Display message - 'Didn't chose directory'
        tk.messagebox.showwarning(title="Błąd", message="Nie podano ścieżki do folderu")
    

    elif entry_path.get()!= "":
        if not os.path.exists(entry_path.get()):
            #Display message - 'Given path is invalid'
            tk.messagebox.showwarning(title="Błąd", message="Wprowadzona ścieżka jest nieprawidłowa")
        
        else:
            #Get path from entry box
            directory.set(entry_path.get())

            #Set initial directory to save current path
            initdir.set(entry_path.get())

            amount.set(len([photo for photo in os.listdir(entry_path.get()) if photo.endswith(PIC_TYPE)]))
            progress_bar.config(maximum=amount.get())
            execute()
    
    elif directory.get()!="":
        if not os.path.exists(entry_path.get()):
            #Display message - 'Given path is invalid'
            tk.messagebox.showwarning(title="Błąd", message="Wprowadzona ścieżka jest nieprawidłowa")
        else:
            directory.set(entry_path.get())
            initdir.set(entry_path.get())
            amount.set(len([photo for photo in os.listdir(entry_path.get()) if photo.endswith(PIC_TYPE)]))
            progress_bar.config(maximum=amount.get())
            execute()
            
def reset_():
    #Display message - 'Do you want to reset?'
    decision=tk.messagebox.askyesno(title="Resetowanie", message="Czy chcesz zresetować?")

    if decision==1:
        progress_bar['value'] = 0
        entry_path.delete(0, tk.END)
        directory.set("")

def execute():
    #While executing script disable all button to prevent errors
    btn_exec['state'] = tk.DISABLED
    btn_reset['state'] = tk.DISABLED

    #Save and reject directories are created in parent directory
    save_path = Path(directory.get()).parent
    reject_path = Path(directory.get()).parent

    #Save and reject directories are created in same given directory
    #save_path = directory.get()
    #reject_path = directory.get()

    #Create names for two directories - finished and rejected
    save_path = str(save_path) + "/Przerobione - " + date
    reject_path = str(reject_path) + "/Odrzut - " + date

    #If name exist (script execued twice in one minute)
    #then next directory name has seconds included 

    if os.path.exists(save_path):
        save_path += today.strftime("-%S")

    if os.path.exists(reject_path):
        reject_path += today.strftime("-%S")  

    #Create directories
    os.mkdir(save_path)
    os.mkdir(reject_path)

    progress_bar['value'] = 0

    mainprogram = imgproc.CropImage(reject_path, save_path, directory.get())
    amount2 = amount.get()

    for _ in range(amount2):
        mainprogram.__next__()
        progress_bar['value'] += 1

    btn_exec['state'] = tk.NORMAL
    btn_reset['state'] = tk.NORMAL

    os.startfile(save_path)
    #Display message - "Finished process"
    tk.messagebox.showinfo(title="Przerobiono", message="Zakończono przerabianie")

font = 'Calibri Light'
bgcolor = "#bababa"

window = tk.Tk()
window.title("Photo cropping")

directory = tk.StringVar()
initdir = tk.StringVar()
amount = tk.IntVar()
initdir.set("C:/")

window.config(background = bgcolor)
window.geometry("650x300")
window.resizable(width=False,height=False)
window.iconbitmap('source_images/icon128.ico')

frame_top = tk.Frame(window,  pady=10, bg=bgcolor)
frame_top.pack()

frame_middle = tk.Frame(window, pady=10,padx=20, bg=bgcolor)
frame_middle.pack()

frame_bottom = tk.Frame(window,bg=bgcolor)
frame_bottom.pack()

img_exec = tk.PhotoImage(file="source_images/exec.png")
img_entry = tk.PhotoImage(file="source_images/pick.png")
img_reset = tk.PhotoImage(file="source_images/reset.png")

label1 = tk.Label(frame_top,text="Podaj folder", bg=bgcolor, font=(font,18))
entry_path = tk.Entry(frame_top, width=38, font=(font, 18), textvariable=directory)
entry_path.xview("end")
btn_getpath = tk.Button(frame_top, image=img_entry, borderwidth=0,bg=bgcolor, command=getFolderPath)

btn_reset = tk.Button(frame_middle, image=img_reset, bg=bgcolor, borderwidth=0, command=reset_)

#Execute script, creates thread to prevent freezing application
btn_exec = tk.Button(frame_middle, image=img_exec,bg=bgcolor ,borderwidth=0,command=lambda: threading.Thread(target=doAction).start())

progress_bar = ttk.Progressbar(frame_bottom,  orient=tk.HORIZONTAL, length=540, mode='determinate')

label1.grid(column=0, row=0, sticky="w")
entry_path.grid(column=0, row=1)
btn_getpath.grid(column=1, row=1, padx=20)

btn_reset.grid(column=1, row=0, padx=10, sticky="w")
btn_exec.grid(column=2, row=0, padx=30, sticky="e")

progress_bar.pack(ipady=10)

window.mainloop()