import face_recognition
import os
import shutil
import cv2
import subprocess
import numpy as np
import pyAesCrypt
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
from tkinter import messagebox
import time
from PIL import Image, ImageTk

# Enroll User
def enroll_face(folder_name, password, ret, frame):
    """Enrolls a new user's face and creates the secure folder"""

    # capture user face
    print("Enrolling\nPlease look into the camera!")

    if not ret:
        print("Failed to capture image! Please try again.")
        return False

    face_encoding = face_recognition.face_encodings(frame)

    if not face_encoding:
        print("No face detected. Please try again.")
        return False

    # create the folder
    os.makedirs(folder_name, exist_ok=True)

    # store the face encoding 
    with open(os.path.join(".face_data"), "wb") as face_data_file:
        face_data_file.write(face_encoding[0].tobytes())
    # Encrypt face encoding
    encrypt_face_data(".face_data", password)


    # Encrypt the folder
    buffer_size = 64 * 1024
    file_name = folder_name + ".tar"
    out_file = file_name + ".aes"
    # Create archive
    subprocess.run(["tar", "-cvf", file_name, folder_name])
    encrypt_file(file_name, out_file, password, buffer_size, folder_name)
    subprocess.run(["rm", file_name])
    print("Enrollment successful!")
    enroll_button.config(state="disabled")
    unlock_button.config(state="normal")
    delete_button.config(state="normal")

    return True

def encrypt_face_data(face_data, password):
    """Encrypts the face data file"""
    buffer_size = 64 * 1024
    with open(face_data, "rb") as f_in:
        with open(face_data + ".aes", "wb") as f_out:
            pyAesCrypt.encryptStream(f_in, f_out, password, buffer_size)
    os.remove(face_data)

def encrypt_file(file_name, out_file, password, buffer_size, folder_name):
    with open(file_name, 'rb') as input_folder:
        with open(out_file, 'wb') as out_folder:
            pyAesCrypt.encryptStream(input_folder, out_folder, password, buffer_size)

    print("Folder encrypted.")

    # Remove original unsecure folder
    subprocess.run(["rm", "-r", folder_name])

    return True

def decrypt_face_data(face_data, password):
    """Decrypts the face data file"""
    buffer_size = 64 * 1024
    with open(face_data, "rb") as f_in:
        try:
            with open(face_data[:-4], "wb") as f_out:
                pyAesCrypt.decryptStream(f_in, f_out, password, buffer_size)
        except ValueError:
            print("Incorrect password of file is corrupted!")
            return False
    return True

def decrypt_file(input_filename, output_filename, password, buffer_size):
    with open(input_filename, 'rb') as input_file:
        with open(output_filename, 'wb') as output_file:
            try:
                print("Trying to decrypt!")
                pyAesCrypt.decryptStream(input_file, output_file, password, buffer_size)
            except ValueError as e:
                print("Decryption Failed: ", e)
                return False
    return True

def browse_files():
    # Function to open file dialog and add selected file to secure folder
    filename = filedialog.askopenfilename(initialdir="/home/ethan", title="Select a File",
                                          filetypes=(("all files", "*.*"),))
    if filename:
        try:
            shutil.copy(filename, "secure_folder")
            print(f"File '{filename}' added to the secure folder.")
            # Update the listbox with the new file
            update_listbox()
        except FileNotFoundError:
            print("File not found.")

def remove_file():
    # Function to remove selected file from secure folder
    selection = listbox.curselection()
    if selection:
        file_index = selection[0]
        file_name = listbox.get(file_index)
        file_path = os.path.join("secure_folder", file_name)
        try:
            os.remove(file_path)
            print(f"File '{file_name}' removed from the secure folder.")
            # Update the listbox after removing the file
            update_listbox()
        except FileNotFoundError:
            print("File not found in the secure folder.")

def update_listbox():
    # Function to update the listbox with the current contents of the secure folder
    listbox.delete(0, tk.END)
    for item in os.listdir("secure_folder"):
        listbox.insert(tk.END, item)

def show_vault_gui(folder_name, password):
    """Displays the vault GUI."""
    global listbox  # Make listbox accessible

    vault_window = create_window("Secure Vault")
    vault_window.geometry("200x400")

    # Create a listbox to display the files
    listbox = tk.Listbox(vault_window)
    listbox.pack(pady=10)

    # Add files to the listbox initially
    update_listbox()

    # Add browse button
    browse_button = ttk.Button(vault_window, text="Browse", command=browse_files)
    browse_button.pack(pady=5)

    # Add remove button
    remove_button = ttk.Button(vault_window, text="Remove", command=remove_file)
    remove_button.pack(pady=5)

    # Add a button to close the vault
    close_button = ttk.Button(vault_window, text="Lock Vault", command=lambda: close_vault(vault_window, folder_name, password))
    close_button.pack(pady=10)

def close_vault(vault_window, folder_name, password):
    """Encrypts the folder and closes the vault window."""
    buffer_size = 64 * 1024
    if not os.listdir(folder_name):
        with open(os.path.join(folder_name, ".dummy"), "w") as f:
            f.write("This is a dummy file.")

    subprocess.run(["tar", "-cvf", folder_name + ".tar", folder_name])
    encrypt_file(folder_name + ".tar", folder_name + ".tar.aes", password, buffer_size, folder_name)
    print("Folder encrypted again.")

    subprocess.run(["rm", folder_name + ".tar"])

    os.remove(".face_data")

    # Re-enable buttons
    children = root.winfo_children()
    for button in range(2, 4):
        children[button].state(['!disabled'])

    vault_window.destroy()

def enroll_gui(folder_name, password):
    """Displays the enrollment GUI."""
    enroll_window = create_window("Face Scan")

    video_label = ttk.Label(enroll_window)
    video_label.pack()

    cap = cv2.VideoCapture(0)

    def show_frames():
        ret, frame = cap.read()
        if ret:
            # Convert the image from BGR to RGB
            cv2image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            # Detect Face and draw rectangle
            face_locations = face_recognition.face_locations(cv2image)
            for (top, right, bottom, left) in face_locations:
                    cv2.rectangle(cv2image, (left, top), (right, bottom), (0, 255, 0), 2)
            # Convert the image to a PIL format
            img = Image.fromarray(cv2image)
            # Convert the PIL image to a Tkinter PhotoImage
            imgtk = ImageTk.PhotoImage(image=img)
            video_label.imgtk = imgtk
            video_label.configure(image=imgtk)
            # Repeat after an interval to capture continiously
            video_label.after(20, show_frames)
    
    show_frames()
    
    def enroll():
        time.sleep(1)
        ret, frame = cap.read()
        if ret:
            enroll_face(folder_name, password, ret, frame)
            children = root.winfo_children()
            # Re-enable buttons
            for button in range(2, 4):
                children[button].state(['!disabled'])
        else:
            print("Failed to capture image!!!")
        cap.release()
        enroll_window.destroy()
    
    enroll_button = ttk.Button(enroll_window, text="Scan", command=enroll)
    enroll_button.pack(pady=10)

def unlock_gui(folder_name, password, unlock_button, delete_button):
    """Displays the unlock GUI."""
    unlock_window = create_window("Unlock Vault")

    # Create label to display the camera feed
    video_label = ttk.Label(unlock_window)
    video_label.pack()

    # Start video capture
    cap = cv2.VideoCapture(0)

    # Func to capture video frames and display
    def show_frames():
        # Capture frame-by-frame
        ret, frame = cap.read()
        if ret:
            # Convert the image from BGR to RGB
            cv2image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # Detect face and draw rectangle
            face_locations = face_recognition.face_locations(cv2image)
            for (top, right, bottom, left) in face_locations:
                try:
                    cv2.rectangle(cv2image, (left, top), (right, bottom), (0, 255, 0), 2)
                except Exception as e:
                    print("Error drawing rectangle:", e)
            # Convert the image to a PIL format
            img = Image.fromarray(cv2image)
            # Convert the PIL image to a Tkinter PhotoImage
            imgtk = ImageTk.PhotoImage(image=img)
            video_label.imgtk = imgtk
            video_label.configure(image=imgtk)
            # Repeat after an interval to capture continiously
            video_label.after(20, show_frames)

    # Display the camera feed
    show_frames()

    # Handle the unlock process
    def unlock(folder_name, password):
        """Unlocks the folder if the user's face matches."""
        time.sleep(1)
        print("Unlocking are you?!!")
        # Decrypt face_data
        if decrypt_face_data(".face_data.aes", password):
            with open(".face_data", "rb") as face_data:
                face_encoding_bytes = face_data.read()
        face_encoding = np.frombuffer(face_encoding_bytes, dtype=np.float64)

        # Capture the user's face using OpenCV
        print("Please look into the camera.")
      
        ret, frame = cap.read()
        cap.release()

        if not ret:
            print("Failed to capture image from camera. Please try again.")
            return

        current_face_encoding = face_recognition.face_encodings(frame)

        if not current_face_encoding:
            print("No face detected. Please try again.")
            return

        # Compare face encodings
        match = face_recognition.compare_faces([face_encoding], current_face_encoding[0])
        if match[0]:
            print("Access granted!")
            # Decrypt the folder
            buffer_size = 64 * 1024
            file_name = folder_name + ".tar"
            out_file = file_name + ".aes"
            # Ensure the encrypted file exists before attempting decryption
            if os.path.exists(out_file):
                decrypt_file(out_file, file_name, password, buffer_size)
                # Extract decrypted file
                subprocess.run(["tar", "-xf", file_name])
                show_vault_gui(folder_name, password)
                unlock_window.destroy()
            else:
                print("Encrypted file not found")
        else:
            print("Access denied.")

    # Add a button to trigger the unlock process
    unlock_button = ttk.Button(unlock_window, text="Unlock", command=lambda: unlock(folder_name, password))
    unlock_button.pack(pady=10)

def on_closing():
    """Handles window close event."""
    print("CLOSING PROGRAM!!")
    # Check if secure_folder exists
    if os.path.exists("secure_folder"):
        close_vault(root, "secure_folder", "tempPass")
    else:
        root.destroy()

def delete_vault_data():
    """Deletes the vault data after confirmation"""
    if messagebox.askyesno("Delete Vault?", "Are you sure you want to delete everything?"):
        # Delete vault data
        print("Deleting vault data...")
        if os.path.exists(".face_data"):
            os.remove(".face_data")
        if os.path.exists("secure_folder.tar.aes"):
            os.remove("secure_folder.tar.aes")
        if os.path.exists(".face_data.aes"):
            os.remove(".face_data.aes")
        messagebox.showinfo("Vault Deleted", "All vault data has been deleted.")
        enroll_button.config(state="normal")
        delete_button.config(state="disabled")
        unlock_button.config(state="disabled")
        print("Deletion Successful")

def create_window(title):
    """Creates a new windows and disables all other windows."""
    new_window = tk.Toplevel(root)
    new_window.title(title)
    children = root.winfo_children()
    # Disable other windows
    for button in range(1, 4):
        children[button].state(['disabled'])  
    return new_window

# Set up the main application window
root = tk.Tk()
root.title("Facial Recognition Vault")
root.geometry("300x250")

# Set Program Icon
# icon = tk.PhotoImage(file="FacialRec-icon.png")
# root.iconphoto(True, icon)

# Set Theme
style = ttk.Style()
style.theme_use('clam')

# Welcome Label
welcome_label = tk.Label(root, text="Welcome to Face Vault", font=("Arial", 12, "bold"))
welcome_label.pack()

# Add Frame for buttons
button_frame = ttk.Frame(root)
button_frame.pack(pady=10)

# Add a button to trigger the enrollment GUI
enroll_button = ttk.Button(root, text="Enroll", command=lambda: enroll_gui("secure_folder", "tempPass"))
enroll_button.pack(padx=20)

# Add a button to trigger the unlock GUI
unlock_button = ttk.Button(root, text="Unlock", command=lambda: unlock_gui("secure_folder", "tempPass", unlock_button, delete_button))
unlock_button.pack(padx=20, pady=10)


# Add a button to delete vault data
delete_button = ttk.Button(root, text="Delete Vault", command=delete_vault_data)
delete_button.pack(padx=20)

# Add version label
version_label = ttk.Label(root, text="Version 0.1", font=("Arial", 10, "bold"))
version_label.pack(pady=20)

# Check if user has already been enrolled
if os.path.exists(".face_data.aes"):
    print("A user is already enrolled!")
    # Disables enroll button
    enroll_button.config(state="disabled")
else:
    unlock_button.config(state="disabled")
    delete_button.config(state="disabled")

# Protocol for handling closing of window
root.protocol("WM_DELETE_WINDOW", on_closing)

root.mainloop()