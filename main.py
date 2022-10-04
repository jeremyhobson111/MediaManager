import tkinter as tk
from tkVideoPlayer import TkinterVideo
from time import sleep


def print_info():
    print(videoplayer.current_duration())


def skip_five_seconds():
    videoplayer.seek(int(videoplayer.current_duration()) + 5)


root = tk.Tk()

videofile = r"\\SKYNET\freeflix\media\fixed_cartoons\Dexter's Laboratory\Season 1\Dexter's Laboratory - s01e01-e03.mkv"

videoplayer = TkinterVideo(master=root, scaled=True)
videoplayer.load(videofile)
videoplayer.pack(expand=True, fill="both")

info_button = tk.Button(text="Info", command=print_info)
info_button.pack()

skip_button = tk.Button(text="Skip", command=skip_five_seconds)
skip_button.pack()

videoplayer.play() # play the video

root.mainloop()
