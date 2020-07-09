from tkinter import *
from tkinter.filedialog import askdirectory
from tkinter import messagebox, filedialog
import tkinter as tk
import string,math,easygui,binascii,hashlib,os,errno,imghdr,time,sys

evidence = []
inpdir = ''

def select_img():
 global evidence, T1
 evidence = filedialog.askopenfilenames(parent = root, initialdir = '/', title = 'Please select files')
 print("Evidences are '{0}'".format(evidence))
 print(len(evidence))
 T1.insert(tk.END,evidence)
 messagebox.showinfo("File selected","Image file is '{0}\n'".format(evidence))

def select_carving_path():
 global inpdir, T2
 inpdir =  askdirectory(parent = root, initialdir = '/', title="Please select folder")
 T2.insert(tk.END,inpdir)
 messagebox.showinfo("Folder selected", "Folder selected is '{0}' ".format(inpdir))

def try_image_png(hex_content, img_no, png_dir) :
    filename = None
    try :
        bytes = binascii.unhexlify(hex_content)
        filename = png_dir + '/png_img%03d.png' % img_no
        f_out = open(filename, 'wb')
        f_out.write(bytes)
        f_out.close()
    except :
        #print("Invalid binascii")
        return
    if imghdr.what(filename) == None :
        os.remove(filename)
        #print("Invalid [imghdr]")
    else :
        #print("**** Image Saved ****") 
        return True

def carve_pngs(evi, inpd) :
    try:
     png_dir = os.path.join(inpd, 'Pngs')
     os.mkdir(png_dir)
    except OSError:
     messagebox.showerror("PNG folder exists", "pngs dir cannot be created as it already exists\nClick OK to proceed")
    print("Carving PNGs\n")
    Buffer_size = 10485760.0  # Bytes (10MB)
    Max_file_size = 1048576.0 # Bytes (1MB)
    SOI = b'89504e47'
    EOI = b'49454e44ae426082'
    pngs_no = 0
    soi_indices = []  # to store header indices 
    eoi_indices = []  # to store trailer indices

    # Get image size
    disk_size = os.path.getsize(evi)
    num_chunks = int(math.ceil(disk_size / Buffer_size))

    curr_chunk = 0
    f_in = open(evi,'rb')
    while True :
        content = f_in.read(int(Buffer_size))    # examine 10 MB of data each time
        if content :    
            print("Examining chunk {0} / {1}". format(curr_chunk + 1, num_chunks))
            hex_content = binascii.hexlify(content)
            index = hex_content.find(SOI, 0)

            while index != -1:  # checking bytes for header
                if (index + 22) < len(hex_content) :
                    header = hex_content[index : index + 22]
                    soi_indices.append(curr_chunk * Buffer_size * 2 + index)
                index = hex_content.find(SOI, index + 4) 
            index = hex_content.find(EOI, 0)

            while index != -1:
                eoi_indices.append(curr_chunk * Buffer_size * 2 + index)
                index = hex_content.find(EOI, index + 4)
            curr_chunk += 1
        else:
            break

    pairs = []
    count = 0
    for soi_i in range(0, len(soi_indices)):    # storing indices of headers and trailers
        for eoi_i in range(0, len(eoi_indices)):
            if (eoi_indices[eoi_i] > soi_indices[soi_i]) and (( eoi_indices[eoi_i] - soi_indices[soi_i])/2 <= Max_file_size):
                pairs.append(( soi_indices[soi_i], eoi_indices[eoi_i] + 4 ))
                break

    print("Second Pass-----")
    curr_chunk = 0
    curr_pair = 0
    f_in = open(evi, 'rb')
    while True :
        content = f_in.read(int(Buffer_size))    # in second examination, trying to retrieve data between soi_indices and eoi_indices and writing into a file 
        if content :
            print("Examining chunk {0}/{1}".format(curr_chunk + 1, num_chunks))     
            hex_content = binascii.hexlify(content)
            while (curr_pair < len(pairs)) and (pairs[curr_pair][0] - (curr_chunk * Buffer_size * 2)) < Buffer_size * 2 :
                #print("Handling pair {0}{1}".format(curr_pair + 1, len(pairs)))
                if pairs[curr_pair][1] > ((curr_chunk + 1) * Buffer_size * 2) :
                    print("Image spans buffer")
                else : 
                    lb = int(pairs[curr_pair][0] - (curr_chunk * Buffer_size * 2))
                    ub = int(pairs[curr_pair][1] - (curr_chunk * Buffer_size * 2))  
                    img = hex_content[lb : ub]
                    if try_image_png(img, pngs_no, png_dir) == True :   # creating a new PNG file
                        pngs_no += 1
                curr_pair += 1
            curr_chunk += 1
        else :
            break
    return pngs_no

                     
def findHeaders_jpg(data) : # to find header pattern
 try :
  return data.index(b'\xff\xd8\xff\xe0')
 except ValueError :
  try:
   return data.index(b'\xff\xd8\xff\xe1')
  except ValueError :
   return -1

def findTermination_jpg(data) :  # to find trailer pattern
 try :
  return data.index(b'\xff\xd8') + 1
 except ValueError :
  return -1

def writeImage_jpg(fobj, location, jpg_dir) : # to write in a jpg file 
    fobj.seek(location)
    global IMG_BLOCK, jpgs_no
    name = jpg_dir + '/jpg_%03d.jpg' % jpgs_no
    try :
        writefobj = open(name, 'wb')    # file to be made (JPG)
    except IOError :
        'Error in file'
    data = fobj.read(IMG_BLOCK)
    while(True) :     # to write bytes till we find next header or trailer
        writefobj.write(data)
        data = fobj.read(IMG_BLOCK)
        location = findHeaders_jpg(data)
        
        termination = findTermination_jpg(data)
        if location >= 0 :    # if next header found 
            print('Broken at Header')
            break
        elif termination >= 0 :   # if trailer found
            print("Trailer found at '{0}'".format(termination))
            break
        elif data == b'' :
            break
    fobj.seek(fobj.tell() - IMG_BLOCK)
    writefobj.close()
    print('Successfully wrote ' + name) 

def carve_jpgs(evi, inpd) :   # Carving JPGs
 global IMG_BLOCK, BLOCK
 print("Carving JPGs\n")
 try:
   jpg_dir = os.path.join(inpd, 'Jpgs')
   os.mkdir(jpg_dir)
 except OSError:
   messagebox.showerror("JPG folder exists", "Jpgs dir cannot be created as it already exists")
 IMG_BLOCK = 512   # to write 512 bytes each time to create a jpg file
 BLOCK = 32  # to read 32 bytes from disk image 
 print("Evidence file is '{0}'".format(evi))
 fobj = open(evi, 'rb')
 data = fobj.read(BLOCK)
 global jpgs_no
 jpgs_no = 0
 while data != b'' :
   location  = findHeaders_jpg(data)
   relative_location = location - BLOCK + fobj.tell()
   if location >= 0 :
      print("Header found at '{0}'".format(location))
      writeImage_jpg(fobj, relative_location, jpg_dir)
      jpgs_no = jpgs_no + 1   # count no of files retrieved so far
   data = fobj.read(BLOCK)    # next data of 16 bytes to find header
 print('Recovered ' + str(jpgs_no) + 'images')
 fobj.close()
 return jpgs_no

def findHeaders_gif(data) :
 try :
  return data.index(b'\x47\x49\x46\x38\x39\x61')
 except ValueError :
  return -1

def findTermination_gif(data) :
 try :
  return data.index(b'\x21\x00\x00\x3b\x00') + 1
 except ValueError :
  return -1

def writeImage_gif(fobj, location, gif_dir) : # to write in a file 
    fobj.seek(location)
    global IMG_BLOCK, gifs_no
    name = gif_dir + '/gif_%03d.gif' % gifs_no
    try :
        writefobj = open(name, 'wb')  # file to be made (JPG)
    except IOError :
        'Error in file'
    data = fobj.read(IMG_BLOCK)
    while True :   # to write bytes till we find next header or trailer
        writefobj.write(data)
        data = fobj.read(IMG_BLOCK)
        location = findHeaders_gif(data)
        termination = findTermination_gif(data)

        if location >= 0: # if next header found 
            print('Broken at Header')
            break
        elif termination >= 0 : # if trailer found
            print("Trailer found at '{0}'".format(termination))
            break
        elif data == b'' :
            break

    fobj.seek(fobj.tell() - IMG_BLOCK)
    writefobj.close()
    print('Successfully wrote ' + name) 
    
def carve_gifs(evi, inpd) :   # Carving GIFs
 print("Carving GIFs\n")
 try:
   gif_dir = os.path.join(inpd, 'Gifs')
   os.mkdir(gif_dir)
 except OSError:
   messagebox.showerror("GIF folder exists", "Gifs dir cannot be created as it already exists")
 global IMG_BLOCK
 IMG_BLOCK = 512
 global BLOCK 
 BLOCK = 32
 print("Evidence file is '{0}'".format(evi))

 fobj = open(evi, 'rb')
 disk_size = os.path.getsize(evi)
 no_of_blocks = disk_size / BLOCK
 print("len of file is '{0}' \nNo of blocks = '{1}'".format(disk_size, no_of_blocks))
 data = fobj.read(BLOCK)
 print("data is '{0}'".format(data))
 global gifs_no
 gifs_no = 0

 while data != b'' :
   location  = findHeaders_gif(data)
   relative_location = location - BLOCK + fobj.tell()
   if location >= 0 :
      print("Header found at '{0}'".format(relative_location))
      writeImage_gif(fobj, relative_location, gif_dir)
      gifs_no = gifs_no + 1  # count no of files retrieved so far
   data = fobj.read(BLOCK)   # next data of 32 bytes to find header
 print('Recovered ' + str(gifs_no) + 'images')
 fobj.close()
 return gifs_no

def select_all() :
 global var1, var2, var3
 var1 = BooleanVar()
 jpg_check = Checkbutton(root, text="jpg", var=var1).place(x=30,y=100)
 var2 = BooleanVar()
 png_check = Checkbutton(root, text="png", var=var2).place(x=30,y=140)
 var3 = BooleanVar()
 gif_check = Checkbutton(root, text="gif", var=var3).place(x=30,y=180)
 var1.set(1)
 var2.set(1)
 var3.set(1)
 print( var1) # var2 var3) # '{3}'".format(var1,var2,var3))

def deselect_all() :
 global var1, var2, var3
 if var1 == False and var2 == False and var3 == False :
  messageerror("Nothing Selected ", "No image type is checked to deselect")
 else :
  var1 = BooleanVar()
  jpg_check = Checkbutton(root, text="jpg", var=var1).place(x=30,y=100)
  var2 = BooleanVar()
  png_check = Checkbutton(root, text="png", var=var2).place(x=30,y=140)
  var3 = BooleanVar()
  gif_check = Checkbutton(root, text="gif", var=var3).place(x=30,y=180)
  var1.set(0)
  var2.set(0)
  var3.set(0)
  
def proceed(jpg,png,gif):
 start = time.time()
 jpgs_ct = 0
 gifs_ct = 0
 pngs_ct = 0
 global evidence, inpdir
 print(jpg.get(),png.get(),gif.get())
 if len(evidence) == 0 or inpdir == "":
  messagebox.showerror("Error", "Please select disk image file or folder first ")
 else:
  for i in range(len(evidence)) :
   try:
    spec_file = os.path.basename(evidence[i])
    print(spec_file)
    spec_dir = os.path.join(inpdir, spec_file + '_images')
    os.mkdir(spec_dir)
   except OSError:
    messagebox.showerror("Problem creating folder", "'{0}' dir already exists in '{1}'\nClick OK to proceed".format(spec_dir, inpdir))
   if jpg.get() == True :
     jpgs_ct = jpgs_ct + carve_jpgs(evidence[i], spec_dir)
   if png.get() == True :
     pngs_ct = pngs_ct + carve_pngs(evidence[i], spec_dir)
   if gif.get() == True :
     gifs_ct = gifs_ct + carve_gifs(evidence[i], spec_dir)
 end = time.time()
 messagebox.showinfo("Images carved","'{0}' jpgs, '{1}' pngs, '{2}' gifs are carved in '{3}' seconds ".format(jpgs_ct, pngs_ct, gifs_ct, end-start))

def pause():
 '''
 t = threading.Thread(target = proceed)
 t.start()
 '''
 choice = messagebox.askquestion("Yes/No", "Are you sure?", icon='warning')
 print("choice is '{0}'".format(choice))
 if choice == 'yes' : 
    sys.exit()

root=Tk()
root.title("Carving Image")

def close_window():
   root.destroy()
l1 = Label(root,text="Evidence :")
l1.place(x=20,y=30)
T1 = Entry(root, width = 30)
T1.place(x=130,y=25, height = 50)
T1.insert(tk.END,evidence)
button1 = Button(root, text=". . .",fg="Red",font="Times", command= select_img)
button1.place(x=380,y=30)

l2 = Label(root, text="Select File Types to carve") 
l2.place(x=20,y=90)

global var1, var2, var3
var1 = BooleanVar()
jpg_check = Checkbutton(root, text="jpg", variable=var1).place(x=30,y=110)
var2 = BooleanVar()
png_check = Checkbutton(root, text="png", variable=var2).place(x=30,y=150)
var3 = BooleanVar()
gif_check = Checkbutton(root, text="gif", variable=var3).place(x=30,y=190)

button2 = Button(root, text="Select_All",fg="Red",font="Times", command= select_all)
button2.place(x=270,y=110)

button2 = Button(root, text="De-Select All",fg="Red",font="Times", command= deselect_all)
button2.place(x=270,y=160)
 
l2 = Label(root,text="Carving Path :")
l2.place(x=20,y=230)
T2 = Entry(root, width = 30)
T2.place(x=130,y=230)
T2.insert(tk.END,inpdir)
button2 = Button(root, text=". . .",fg="Red",font="Times", command= select_carving_path)
button2.place(x=380,y=230)

l3 = Label(root,text="Click Start to proceed ")
l3.place(x=20,y=270)

Button(root, text='Start',fg="green", command= lambda: proceed(var1,var2,var3)).place(x=300,y=270)

Button(root, text='Stop',fg="green", command= pause).place(x=300,y=310)

Button(root, text='Close',fg="red",font="Times",command=close_window).pack(side="bottom")
root.geometry("500x500")
mainloop()
