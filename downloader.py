import os
import asyncio
import tkinter as tk, tkinter.filedialog
import urllib.request
from bs4 import BeautifulSoup
from collections import namedtuple
import tqdm

SITE_BASE = "http://www.zemirotdatabase.org/"
Song = namedtuple("Song", "name value")

def song_list_generator(path):
    """
    This function yields song_name and url address for each song in the list.
    Currently the first result is a link
    """
    with urllib.request.urlopen(path) as response:
        soup = BeautifulSoup(response.read(), 'html.parser')
        content = soup.find("div", {"id":"content"})
        yield from ((x.getText(),x.find('a').get('href'))
                    for x in content.findAll('li'))


@asyncio.coroutine
def download_coro(filename, songs):
    CONCUR_REQ = 5
    semaphore = asyncio.Semaphore(CONCUR_REQ)
    to_do = [download_song(song, semaphore) for song in songs]

    to_do_iter = asyncio.as_completed(to_do)
    to_do_iter = tqdm.tqdm(to_do_iter, total=len(to_do))
    with open(filename, "w") as file:
        for future in to_do_iter:
            result = yield from future
            file.write(result.name + "\n"*2 +
                       result.value + "\n"*3)

@asyncio.coroutine
def download_song(song, semaphore):
    with (yield from semaphore):
        with urllib.request.urlopen(SITE_BASE + song.value) as response:
            soup = BeautifulSoup(response.read(), 'html.parser')
            content = soup.find("div", {"id":"hebrew"})
            return Song(song.name, content.getText())


class Application(tk.Frame):
    def __init__(self, master=None):
        super().__init__(master)
        self.songs_states = {}
        self.pack()
        self.create_widgets()
        self.create_scrolltext()

    def create_scrolltext(self):
        # Scrollable chechbuttons:
        # https://stackoverflow.com/questions/5860675/variable-size-list-of-checkboxes-in-tkinter
        self.song_frame = tk.Frame(self)
        vsb = tk.Scrollbar(self.song_frame, orient="vertical")
        text = tk.Text(self.song_frame, width=80, height=90,
                            yscrollcommand=vsb.set)
        vsb.config(command=text.yview)
        vsb.pack(side="right", fill="y")
        text.pack(side="left", fill="both", expand=True)
        self.song_frame.pack()

        for item in song_list_generator(SITE_BASE+"song_index.php"):
            song, path = item
            indicator = tk.IntVar()
            self.songs_states.setdefault(song, (indicator, path))
            cb = tk.Checkbutton(self.song_frame, variable=indicator, text=song)
            text.window_create("end", window=cb)
            text.insert("end", "\n")
        text.config(state="disabled")

    def create_widgets(self):
        self.update_songs = tk.Button(self)
        self.update_songs["text"] = "Download songs"
        self.update_songs["command"] = self.save_selected
        self.update_songs.pack(side="top")

        self.quit = tk.Button(self, text="QUIT", fg="red",
                              command=root.destroy)
        self.quit.pack(side="bottom")

    def save_selected(self):
        filename = tk.filedialog.asksaveasfilename(initialdir = os.getcwd(),
                                                        initialfile = "downloaded_songs",
                                                        title = "Select file",
                                                        defaultextension=".txt")
        loop = asyncio.get_event_loop()
        coro = download_coro(filename, (Song(key, value[1])
                             for (key, value) in self.songs_states.items()
                             if value[0].get() == 1))
        loop.run_until_complete(coro)


if __name__ == "__main__":
    root = tk.Tk()
    app = Application(master=root)
    app.mainloop()
