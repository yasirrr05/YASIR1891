import wave
import numpy as np
import os
import struct
from tkinter import *
from tkinter import filedialog
from stegano.lsb import lsb
from PIL import Image
import cv2

def move_text():
    global x_pos
    if x_pos > logo_x + logo_width + 10:  # Stop right next to the logo with a margin
        title_label.place(x=x_pos, y=20)
        x_pos -= 5  # Adjust the speed of motion (lower values = slower)
        root.after(20, move_text)  # Call the function repeatedly every 20ms
    else:
        title_label.place(x=logo_x + logo_width + 10, y=20)  # Stop precisely next to the logo


def fade_buttons():
    global btn_opacity
    if btn_opacity < 1.0:  # Maximum opacity value
        for button in buttons:
            # Adjust button appearance using the current opacity
            r, g, b = 47, 65, 85  # Frame background color
            bg_color = f"#{int(r * (1 - btn_opacity)):02x}{int(g * (1 - btn_opacity)):02x}{int(b * (1 - btn_opacity)):02x}"
            button.config(bg=bg_color,
                          fg=f"#{int(255 * btn_opacity):02x}{int(255 * btn_opacity):02x}{int(255 * btn_opacity):02x}")
        btn_opacity += 0.05  # Adjust speed of fade-in
        root.after(50, fade_buttons)  # Call this function again after 50ms

# GUI Application
root = Tk()
root.title("Hybrid Steganography")
root.geometry("700x600+150+180")
root.resizable(False, False)
root.config(bg="#2f4155")

# Global variables
filename = ""
file_type = ""

# Add the logo
logo = PhotoImage(file="Icon.png")  # Replace with your logo path
logo_label = Label(root, image=logo, bg="#2f4155")
logo_label.place(x=10, y=0)

# Get the logo's position and size
logo_x = 10  # The x-coordinate of the logo
logo_width = logo.width()  # Dynamically get the width of the logo

# Starting position of the text
x_pos = 700  # Start from off-screen on the right

# Create the title label
title_label = Label(root, text="Hybrid Steganography", bg="#2f4155", fg="white", font="arial 20 bold")

# Start the motion
move_text()


# Function to select a file (image or audio)
def select_file():
    global filename, file_type
    filename = filedialog.askopenfilename(
        initialdir=os.getcwd(),
        title="Select Image or Audio File",
        filetypes=(
            ("PNG Files", "*.png"),
            ("JPEG Files", "*.jpg;*.jpeg"),
            ("WAV Files", "*.wav"),
            ("All Files", "*.*"),
        ),
    )

    if filename:
        if filename.lower().endswith(".png"):
            file_type = "png"
            text1.delete(1.0, END)
            text1.insert(END, "PNG file selected. You can now hide data.")
        elif filename.lower().endswith((".jpg", ".jpeg")):
            file_type = "jpeg"
            text1.delete(1.0, END)
            text1.insert(END, "JPEG file selected. You can now hide data.")
        elif filename.lower().endswith(".wav"):
            file_type = "audio"
            text1.delete(1.0, END)
            text1.insert(END, "Audio file selected. You can now hide data.")
        else:
            file_type = ""
            text1.config(state=NORMAL)
            text1.delete(1.0, END)
            text1.insert(END, "Unsupported file type. Please select a valid image or audio file.")
            text1.config(state=DISABLED)


# Function to hide data in PNG
def hide_data_in_png(png_path, message, output_path):
    secret = lsb.hide(png_path, message)
    secret.save(output_path)


# Function to reveal data from PNG
def reveal_data_in_png(png_path):
    return lsb.reveal(png_path)


# Function to hide data in JPEG
def hide_data_in_jpeg(jpeg_path, message, output_path):
    message_binary = ''.join(format(ord(c), '08b') for c in message) + "11111111"  # EOF marker
    image = cv2.imread(jpeg_path, cv2.IMREAD_UNCHANGED)
    if image is None:
        text1.config(state=NORMAL)
        raise ValueError("Invalid JPEG file.")
    text1.config(state=DISABLED)

    ycrcb = cv2.cvtColor(image, cv2.COLOR_BGR2YCrCb)
    y_channel = ycrcb[:, :, 0]

    height, width = y_channel.shape
    message_index = 0
    for i in range(0, height, 8):
        for j in range(0, width, 8):
            block = y_channel[i:i + 8, j:j + 8]
            dct_block = cv2.dct(np.float32(block) - 128)

            flat_block = dct_block.flatten()
            for k in range(len(flat_block)):
                if flat_block[k] != 0 and message_index < len(message_binary):
                    coeff = round(flat_block[k])
                    coeff = (coeff & ~1) | int(message_binary[message_index])
                    flat_block[k] = coeff
                    message_index += 1

            dct_block = flat_block.reshape((8, 8))
            y_channel[i:i + 8, j:j + 8] = cv2.idct(dct_block) + 128

            if message_index >= len(message_binary):
                break
        if message_index >= len(message_binary):
            break

    ycrcb[:, :, 0] = y_channel
    modified_image = cv2.cvtColor(ycrcb, cv2.COLOR_YCrCb2BGR)
    cv2.imwrite(output_path, modified_image)


# Function to reveal data from JPEG
def reveal_data_in_jpeg(jpeg_path):
    image = cv2.imread(jpeg_path, cv2.IMREAD_UNCHANGED)
    if image is None:
        text1.config(state=NORMAL)
        raise ValueError("Invalid JPEG file.")
    text1.config(state=DISABLED)

    ycrcb = cv2.cvtColor(image, cv2.COLOR_BGR2YCrCb)
    y_channel = ycrcb[:, :, 0]

    binary_message = ""
    for i in range(0, y_channel.shape[0], 8):
        for j in range(0, y_channel.shape[1], 8):
            block = y_channel[i:i + 8, j:j + 8]
            dct_block = cv2.dct(np.float32(block) - 128)

            for coeff in dct_block.flatten():
                if coeff != 0:
                    coeff = round(coeff)
                    binary_message += str(coeff & 1)

    chars = [binary_message[i:i + 8] for i in range(0, len(binary_message), 8)]
    message = ''.join([chr(int(char, 2)) for char in chars])
    return message.split(chr(255))[0]


# Function to hide a message in an audio file using LSB
def hide_audio_message(audio_path, message, output_path):
    message_binary = ''.join(format(ord(char), '08b') for char in message)
    message_length = len(message_binary)

    with wave.open(audio_path, 'rb') as audio:
        params = audio.getparams()
        num_channels = params.nchannels
        sample_width = params.sampwidth
        num_frames = params.nframes

        if sample_width != 2:
            raise ValueError("Only 16-bit WAV files are supported.")

        frames = audio.readframes(num_frames)
        frame_list = list(struct.unpack("<" + "h" * num_frames * num_channels, frames))

    if len(message_binary) > len(frame_list):
        raise ValueError("Message is too long to fit in the selected audio file.")


    length_binary = format(message_length, '032b')
    for i in range(32):
        frame_list[i] = (frame_list[i] & ~1) | int(length_binary[i])

    for i in range(message_length):
        frame_list[32 + i] = (frame_list[32 + i] & ~1) | int(message_binary[i])

    modified_frames = struct.pack("<" + "h" * len(frame_list), *frame_list)

    with wave.open(output_path, 'wb') as modified_audio:
        modified_audio.setparams(params)
        modified_audio.writeframes(modified_frames)


# Function to reveal a hidden message from an audio file
def reveal_audio_message(audio_path):
    audio = wave.open(audio_path, 'rb')
    frames = np.frombuffer(audio.readframes(audio.getnframes()), dtype=np.int16)
    audio.close()

    binary_message = ''.join(str(frame & 1) for frame in frames)
    chars = [binary_message[i:i + 8] for i in range(0, len(binary_message), 8)]
    decoded_message = ''.join([chr(int(char, 2)) for char in chars])
    return decoded_message.split("<<<EOF>>>")[0]


# Function to hide data based on the file type
def hide_data():
    if not filename or not file_type:
        text1.config(state=NORMAL)
        text1.delete(1.0, END)
        text1.insert(END, "Please select a file first.")
        text1.config(state=DISABLED)
        return

    message = text1.get(1.0, END).strip()
    if not message:
        text1.delete(1.0, END)
        text1.insert(END, "Please enter a message to hide.")
        return

    file_extension = ".png" if file_type == "png" else ".jpg" if file_type == "jpeg" else ".wav"
    output_file = filedialog.asksaveasfilename(defaultextension=file_extension,
                                               filetypes=(("PNG Files", "*.png"),
                                                          ("JPEG Files", "*.jpg;*.jpeg"),
                                                          ("WAV Files", "*.wav"),
                                                          ("All Files", "*.*")))

    try:
        if file_type == "png":
            hide_data_in_png(filename, message, output_file)
        elif file_type == "jpeg":
            hide_data_in_jpeg(filename, message, output_file)
        elif file_type == "audio":
            hide_audio_message(filename, message, output_file)

        text1.config(state=NORMAL)
        text1.delete(1.0, END)
        text1.insert(END, f"Data successfully hidden in {output_file}.")
        text1.config(state=DISABLED)
    except Exception as e:
        text1.config(state=NORMAL)
        text1.delete(1.0, END)
        text1.insert(END, f"Error: {str(e)}")
        text1.config(state=DISABLED)


# Function to show data based on the file type
def show_data():
    global filename, file_type
    filename = filedialog.askopenfilename(initialdir=os.getcwd(),
                                          title="Select Image or Audio File",
                                          filetypes=(("PNG Files", "*.png"),
                                                     ("JPEG Files", "*.jpg;*.jpeg"),
                                                     ("WAV Files", "*.wav"),
                                                     ("All Files", "*.*")))
    if not filename:
        text1.config(state=NORMAL)
        text1.delete(1.0, END)
        text1.insert(END, "No file selected.")
        text1.config(state=DISABLED)
        return

    try:
        if filename.lower().endswith(".png"):
            hidden_message = reveal_data_in_png(filename)
            text1.config(state=NORMAL)
            text1.delete(1.0, END)
            text1.insert(END, f"Hidden message: {hidden_message}")
            text1.config(state=DISABLED)
        elif filename.lower().endswith((".jpg", ".jpeg")):
            hidden_message = reveal_data_in_jpeg(filename)
            text1.config(state=NORMAL)
            text1.delete(1.0, END)
            text1.insert(END, f"Hidden message: {hidden_message}")
            text1.config(state=DISABLED)
        elif filename.lower().endswith(".wav"):
            hidden_message = reveal_audio_message(filename)
            text1.config(state=NORMAL)
            text1.delete(1.0, END)
            text1.insert(END, f"Hidden message: {hidden_message}")
            text1.config(state=DISABLED)
        else:
            text1.config(state=NORMAL)
            text1.delete(1.0, END)
            text1.insert(END, "Unsupported file type for extracting data.")
            text1.config(state=NORMAL)
    except Exception as e:
        text1.config(state=NORMAL)
        text1.delete(1.0, END)
        text1.insert(END, f"Error: {str(e)}")
        text1.config(state=DISABLED)

# Frames and buttons
frame1 = Frame(root, bd=3, bg="black", width=340, height=280, relief=GROOVE)
frame1.place(x=10, y=80)
lbl = Label(frame1, bg="black", text="No File Selected", font="arial 10", fg="white")
lbl.place(x=40, y=10)

frame2 = Frame(root, bd=3, width=340, height=280, bg="white", relief=GROOVE)
frame2.place(x=350, y=80)
text1 = Text(frame2, font="Robote 20", bg="white", fg="black", relief=GROOVE)
text1.place(x=0, y=0, width=320, height=295)
scrollbar1 = Scrollbar(frame2)
scrollbar1.place(x=320, y=0, height=300)
scrollbar1.configure(command=text1.yview)
text1.configure(yscrollcommand=scrollbar1.set)

frame3 = Frame(root, bd=3, bg="#2f4155", width=500, height=100, relief=GROOVE)
frame3.place(x=102, y=410)  # Positioned below the two frames

Label(frame3, text="Image / Audio Files", bg="#2f4155", fg="yellow", font="arial 12 bold").place(relx=0.5, rely=0.1, anchor=CENTER)

#buttons in frame3
buttons = [
# Button(frame3, text="Select File", width=10, height=2, font="arial 14 bold", command=select_file).place(x=10, y=30)
# Button(frame3, text="Hide Data", width=10, height=2, font="arial 14 bold", command=hide_data).place(x=150, y=30)
# Button(frame3, text="Show Data", width=10, height=2, font="arial 14 bold", command=show_data).place(x=290, y=30)
    Button(frame3, text="Select File", width=10, height=2, font="arial 12 bold", command=select_file),
    Button(frame3, text="Hide Data", width=10, height=2, font="arial 12 bold", command=hide_data),
    Button(frame3, text="Show Data", width=10, height=2, font="arial 12 bold", command=show_data),
]

# Initial placement of buttons (outside visible range)
btn_opacity = 0.0  # Initial relative vertical position for fade motion
x_positions = [0.2, 0.5, 0.8]  # Horizontal positions for buttons in the frame

for btn, xpos in zip(buttons, x_positions):
    btn.place(relx=xpos, rely=0.6, anchor=CENTER)  # Initially hidden below the frame

# Start fade-in animation for buttons
fade_buttons()

root.mainloop()