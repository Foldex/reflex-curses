#!/usr/bin/env python
"""A TUI/CLI streamlink wrapper"""
# TODO Getting Big, Separate into different modules

import configparser
import curses
import shlex
import sys
from os import path, makedirs
from random import randint
from shutil import copyfile
from subprocess import Popen, PIPE, DEVNULL
from textwrap import wrap
from time import sleep
from urllib.parse import quote, unquote

import requests

VERSION = "0.9.4"


class Config:
    """Configuration Variables and Locally Followed Twitch Channels."""

    def __init__(self):
        self.config_dir = path.expanduser("~/.config/reflex-curses")
        self.followed = {}
        self.cp = configparser.ConfigParser()

        # Setup Default Values
        self.cp["keys"] = {
            "add": "a",  # Add channel follow / Show all followed
            "chat": "c",  # Open chat with chat_method
            "delete": "d",  # Delete channel from followed list
            "followed": "f",  # Switch to followed view
            "game": "g",  # Search by Game Name (exact)
            "back": "h",  # Go to initial view
            "import": "i",  # Import follows from twitch user
            "down": "j",  # Move cursor down
            "up": "k",  # Move cursor up
            "forward": "l",  # Enter menu or launch stream
            "online": "o",  # Toggle online/all streams in followed list
            "quit": "q",  # Quit
            "refresh": "r",  # Resend last query
            "t_stream": "s",  # Go to top streams view
            "t_game": "t",  # Go to top games view
            "search": "/",  # Search for streams
            "vods": "v",  # Go to VOD view
            "yank": "y",  # Yank channel url
            "page+": "n",  # Next Page
            "page-": "p",  # Previous page
            "qual+": "=",  # Select higher quality
            "qual-": "-",  # Select lower quality
        }

        self.cp["exec"] = {
            "browser": "firefox --new-window",
            "chat_method": "browser",  # browser/weechat/irc
            "player": "mpv --force-window=yes",
            "streamlink": "streamlink -t '{author} - {title}' --twitch-disable-hosting --twitch-disable-ads",
            "term": "urxvt -e",
        }

        self.cp["twitch"] = {
            "client_id": "caozjg12y6hjop39wx996mxn585yqyk",
            "lang": "",  # Language filter
            # API limit is 100, but API seems to choke at higher than 75
            "results_limit": 75,  # Max number of results for a query
            "retry_limit": 3,  # Max number of retries for a query
        }

        self.cp["ui"] = {
            # Supported Colors: black/blue/cyan/green/magenta/white/yellow/red
            "default_state": "games",  # Initial view: games/followed/streams
            "hl_color": "blue",  # Color of selected item highlight
            "l_win_color": "white",  # Color of left window
            "r_win_color": "green",  # Color of right window
            "quality": "best",  # Default quality selection
            "show_borders": "True",  # Display Window Borders
            "show_keys": "True",  # Display Keybinds
        }

        self.cp["irc"] = {
            "address": "irc.chat.twitch.tv",  # Address of the irc server, weechat only
            "network": "reflex",  # Name of the saved network
            "no_account": "True",  # Use a random justinfan nick to connect, weechat only
            "port": "6697",  # Port of the irc server, weechat only
        }

        # Read in Config File
        self.cp.read(self.config_dir + "/config")

    def write_config(self):
        """Writes config to file"""
        with open(self.config_dir + "/config", "w") as configfile:
            self.cp.write(configfile)

    def init_followed_list(self):
        """Loads the file containing followed channels.
        Will make config_dir if it doesn't exist.
        File Format: 'channel_name twitch_api_id'
        """
        file_path = f"{self.config_dir}/followed"

        if not path.isdir(self.config_dir):
            makedirs(self.config_dir)
        if path.isfile(file_path):
            file = open(file_path, "r")
            for line in file:
                (name, api_id) = (line.split() + [None])[:2]
                # Fetch IDs if we dont have one
                # TODO Batch Requests?
                if api_id is None:
                    api_id = twitch.get_twitch_id(name)

                self.followed[name] = api_id
            file.close()

    def import_follows_from_user(self, username, overwrite=False):
        """Adds twitch user's follow list to your own"""

        user_id = twitch.get_twitch_id(username)
        twitch.request(["get_follows", user_id])

        if not twitch.data:
            return

        if overwrite:
            config.followed = {}

        # TODO Paginate follows > results_limit
        for result in twitch.data["follows"]:
            # print(f'{follow["channel"]["name"]}: {follow["channel"]["_id"]}')
            if result["channel"]["name"] not in config.followed:
                config.followed[result["channel"]["name"]] = str(result["channel"]["_id"])

    def write_followed_list(self):
        """Write followed channels list to file, backing up old one."""
        file_path = f"{self.config_dir}/followed"
        self.backup(file_path)

        file = open(file_path, "w")
        for i in sorted(self.followed, key=str.lower):
            file.write(f"{i} {self.followed[i]}\n")
        file.close()

    def backup(self, file_path):
        """Takes input path, copies file to file.old."""
        if path.isfile(file_path):
            backup_path = file_path + ".old"
            copyfile(file_path, backup_path)


class Interface:
    """Curses Interface to display results from Twitch Queries."""

    def __init__(self):
        self.screen = curses.initscr()
        curses.noecho()
        curses.cbreak()
        curses.curs_set(0)
        self.screen.keypad(1)

        if curses.has_colors():
            colorlist = {
                "black": curses.COLOR_BLACK,
                "blue": curses.COLOR_BLUE,
                "cyan": curses.COLOR_CYAN,
                "green": curses.COLOR_GREEN,
                "magenta": curses.COLOR_MAGENTA,
                "white": curses.COLOR_WHITE,
                "yellow": curses.COLOR_YELLOW,
                "red": curses.COLOR_RED,
            }

            curses.start_color()
            curses.use_default_colors()
            curses.init_pair(1, colorlist[config.cp["ui"]["hl_color"]], -1)
            curses.init_pair(2, colorlist[config.cp["ui"]["r_win_color"]], -1)
            curses.init_pair(3, colorlist[config.cp["ui"]["l_win_color"]], -1)
            self.hl_1 = curses.color_pair(1)
            self.hl_2 = curses.color_pair(2)
            self.hl_3 = curses.color_pair(3)
        else:
            self.hl_1 = 0
            self.hl_2 = 0
            self.hl_3 = 0

        self.state = "top"
        self.f_filter = "online"

        self.quality = ["audio_only", "worst", "360p", "480p", "720p", "1080p", "best"]
        self.cur_quality = self.quality.index(config.cp["ui"]["quality"])

        self.cache = 0
        self.cur_page = []
        self.donothing = False
        self.maxitems = 0
        self.page = 0
        self.page_cache = 0
        self.sel = 0
        self.sel_cache = 0

        self.init_screen()

    def init_screen(self):
        """Initializes the screen.
        Is also called when the terminal is resized.
        """
        self.screen.clear()
        self.size = self.screen.getmaxyx()
        if self.check_term_size():
            return
        self.maxlen = self.size[1] // 2 - 4
        self.maxitems = self.size[0] // 2 - 1
        self.draw_logo()
        self.win_l = curses.newwin(self.size[0], self.size[1] // 2, 0, 0)
        self.win_r = curses.newwin(self.size[0], self.size[1] // 2, 0, self.size[1] // 2)

        self.screen.move(0, 0)
        self.screen.refresh()

    def draw_logo(self):
        """Displays the logo on initial startup"""
        if self.size[1] > 90:
            logo = (
                "            __ _                                               \n"
                "  _ __ ___ / _| | _____  __      ___ _   _ _ __ ___  ___  ___  \n"
                " | '__/ _ \\ |_| |/ _ \\ \\/ /____ / __| | | | '__/ __|/ _ \\/ __| \n"
                " | | |  __/  _| |  __/>  <_____| (__| |_| | |  \\__ \\  __/\\__ \\ \n"
                " |_|  \\___|_| |_|\\___/_/\\_\\     \\___|\\__,_|_|  |___/\\___||___/ \n"
            )
            logo_height = len(logo.splitlines()) + 1
            for i, line in enumerate(logo.splitlines(), 2):
                self.screen.addnstr(
                    self.size[0] // 2 - (logo_height - i),
                    self.size[1] // 2 - (len(line) // 2),
                    line,
                    self.maxlen,
                    self.hl_2,
                )

        else:
            self.screen.addnstr(
                self.size[0] // 2 - 1, self.size[1] // 2 - 5, "Loading...", self.maxlen
            )

    def set_state(self, new_state):
        """Set the screen state and resets selection/page number.
        state is used to determine what kind of data is shown.
        """
        self.state = new_state
        self.sel_cache = self.sel
        self.page_cache = self.page
        self.reset_page()

    def win_blink(self):
        """Visually blink the screen."""
        self.screen.clear()
        self.screen.refresh()

    def reset_page(self, reset_cache=False):
        """Reset selection and page number, optionally resets cache as well."""
        self.sel = 0
        self.page = 0
        if reset_cache:
            self.sel_cache = 0
            self.page_cache = 0

    def check_term_size(self):
        """Check if Terminal is too small to display content"""
        if self.size[0] < 10 or self.size[1] < 32:
            return True

    def warn_term_size(self):
        """Pop a warning if term is too small to display content."""
        self.screen.clear()
        if self.size[0] > 2 and self.size[1] > 16:
            self.screen.addstr(0, 0, "Terminal")
            self.screen.addstr(1, 0, "too small")

    def set_cur_page(self):
        """Produce a slice of the data returned by Twitch for the current page.
        Different states need different json.
        """
        start = self.maxitems * self.page
        end = self.maxitems * (self.page + 1)

        if twitch.data:
            if self.state == "top":
                self.cur_page = twitch.data["top"][start:end]
            elif self.state == "search" or self.state == "follow" and self.f_filter == "online":
                self.cur_page = twitch.data["streams"][start:end]
            elif self.state == "follow" and self.f_filter == "all":
                self.cur_page = list(config.followed)[start:end]
            elif self.state == "vods":
                self.cur_page = twitch.data["videos"][start:end]
        else:
            self.cur_page = []

    def prompt(self, text):
        """Prompt user for text input in new popup window, return the text.
        If nothing was entered, kill the window.
        Used for searching for streams and game name.
        """
        win = curses.newwin(3, self.size[1] // 2 - 4, self.size[0] // 2 - 1, self.size[1] // 4)
        win.border(0)
        win.addnstr(0, 3, text, self.size[0] - 4)
        win.refresh()
        curses.echo()
        string = win.getstr(1, 1, self.size[1] - 6)
        if not string:
            win.clear()
        return string

    def draw_win_l(self):
        """Display the left half of the screen.
        Left window is used for displaying Twitch data and making selections.
        """
        self.win_l.erase()
        if config.cp.getboolean("ui", "show_borders"):
            self.win_l.border(0)
        index = 0

        for i in self.cur_page:
            if index >= self.maxitems:
                break

            if self.state == "top":
                string = str(i["game"]["name"])
            elif self.state == "vods":
                string = str(i["title"]).replace("\n", "")
                # truncate long vod titles
                if len(string) > self.maxlen // 2:
                    string = string[: self.maxlen // 2] + "..."
                string += " - " + str(i["game"])
            elif self.state == "search" or (self.state == "follow" and self.f_filter == "online"):
                string = str(i["channel"]["display_name"])
                if twitch.query[0] != "game":
                    string += " - " + str(i["game"])
            elif self.state == "follow" and self.f_filter == "all":
                string = str(i)

            if index == self.sel:
                self.win_l.addnstr(
                    index * 2 + 2, 2, string, self.maxlen, curses.A_UNDERLINE | self.hl_1,
                )
            else:
                self.win_l.addnstr(index * 2 + 2, 2, string, self.maxlen, self.hl_3)
            index += 1

        self.win_l.addnstr(
            self.size[0] - 2, self.size[1] // 2 - 9, f" page:{self.page + 1}", self.maxlen,
        )

        self.draw_win_l_headers()

    def draw_win_l_headers(self):
        """Displays Headers in game view and vod view"""
        if self.state == "search" and twitch.query[0] == "game":
            text = unquote(twitch.query[1])
            t_len = len(text)
            self.win_l.addnstr(1, self.size[1] // 2 - (t_len + 2), text, self.maxlen)
            self.win_l.hline(2, self.size[1] // 2 - (t_len + 2), curses.ACS_HLINE, t_len)
        elif self.state == "vods":
            text = "VODs"
            t_len = len(text)
            self.win_l.addnstr(1, self.size[1] // 2 - (t_len + 2), text, self.maxlen)
            self.win_l.hline(2, self.size[1] // 2 - (t_len + 2), curses.ACS_HLINE, t_len)

        self.win_l.refresh()

    def draw_win_r(self):
        """Display right half of the screen.
        Right window is used for displaying additional info like descriptions.
        """
        self.win_r.erase()
        if config.cp.getboolean("ui", "show_borders"):
            self.win_r.border(0)
        self.draw_keys()
        index = 0

        for i in self.cur_page:
            if index >= self.maxitems:
                break

            if index != self.sel:
                index += 1
                continue

            if self.state == "top":
                self.win_r.addnstr(2, 3, f"Viewers: {i['viewers']}", self.maxlen, self.hl_2)
                self.win_r.addnstr(3, 3, f"Channels: {i['channels']}", self.maxlen, self.hl_2)
            elif self.state == "vods":
                m, s = divmod(i["length"], 60)
                h, m = divmod(m, 60)

                self.win_r.addnstr(2, 3, f"Date: {i['created_at']}", self.maxlen, self.hl_2)
                self.win_r.addnstr(3, 3, f"Views: {i['views']}", self.maxlen, self.hl_2)
                self.win_r.addnstr(4, 3, f"Length: {h:02}:{m:02}:{s:02}", self.maxlen, self.hl_2)
                self.win_r.addnstr(5, 3, f"Status: {i['status']}", self.maxlen, self.hl_2)
            elif self.state == "search" or (self.state == "follow" and self.f_filter == "online"):
                self.win_r.addnstr(
                    self.size[0] - 3,
                    2,
                    "quality: " + config.cp["keys"]["qual-"] + config.cp["keys"]["qual+"],
                    self.maxlen,
                )
                self.win_r.addnstr(
                    self.size[0] - 2, 3, self.quality[self.cur_quality], self.maxlen
                )
                self.win_r.addnstr(2, 3, str(i["channel"]["url"]), self.maxlen, self.hl_2)
                self.win_r.addnstr(
                    4, 3, f"Language: {i['channel']['language']}", self.maxlen, self.hl_2,
                )
                self.win_r.addnstr(5, 3, f"Viewers: {i['viewers']}", self.maxlen, self.hl_2)
                self.win_r.addnstr(6, 3, "Status:", self.maxlen, self.hl_2)
                status = wrap(str(i["channel"]["status"]), self.size[1] // 2 - 6)
                l_num = 7
                for line in status:
                    if l_num >= self.size[0] - 4:
                        break
                    self.win_r.addstr(l_num, 4, line, self.hl_2)
                    l_num += 1
                    # TODO Clean up
                    # Lazy way of setting cursor position to display stderr
                    # output from streamlink. A large enough error message
                    # will vomit on the screen
                self.win_r.addstr(l_num, 4, "", self.hl_2)
            index += 1

        self.win_r.refresh()

    def draw_keys(self):
        """Displays keybinds for each page in the right hand window."""
        if not config.cp.getboolean("ui", "show_keys"):
            return

        if self.state == "top":
            items = [
                f"back: {config.cp['keys']['back']}",
                f"search: {config.cp['keys']['search']}",
                f"followed: {config.cp['keys']['followed']}",
                f"game: {config.cp['keys']['game']}",
                f"top streams: {config.cp['keys']['t_stream']}",
                f"refresh: {config.cp['keys']['refresh']}",
                f"quit: {config.cp['keys']['quit']}",
            ]
        elif self.state in ("search", "vods"):
            items = [
                f"back: {config.cp['keys']['back']}",
                f"search: {config.cp['keys']['search']}",
                f"add follow: {config.cp['keys']['add']}",
                f"chat: {config.cp['keys']['chat']}",
                f"followed: {config.cp['keys']['followed']}",
                f"game: {config.cp['keys']['game']}",
                f"refresh: {config.cp['keys']['refresh']}",
                f"top streams: {config.cp['keys']['t_stream']}",
                f"top games: {config.cp['keys']['t_game']}",
                f"vods: {config.cp['keys']['vods']}",
                f"yank: {config.cp['keys']['yank']}",
                f"quit: {config.cp['keys']['quit']}",
            ]
        elif self.state == "follow":
            items = [
                f"back: {config.cp['keys']['back']}",
                f"search: {config.cp['keys']['search']}",
                f"chat: {config.cp['keys']['chat']}",
                f"delete: {config.cp['keys']['delete']}",
                f"game: {config.cp['keys']['game']}",
                f"import: {config.cp['keys']['import']}",
                f"online/all: {config.cp['keys']['online']}",
                f"refresh: {config.cp['keys']['refresh']}",
                f"top streams: {config.cp['keys']['t_stream']}",
                f"top games: {config.cp['keys']['t_game']}",
                f"vods: {config.cp['keys']['vods']}",
                f"yank: {config.cp['keys']['yank']}",
                f"quit: {config.cp['keys']['quit']}",
            ]
        else:
            items = []

        length = len(items)

        # only draw keys if it takes up less than half the vertical space
        if self.size[0] // 2 > length:
            for i in items:
                self.win_r.addnstr(
                    self.size[0] - (length + 1), self.size[1] // 2 - (len(i) + 2), i, self.maxlen,
                )
                length -= 1


class Keybinds:
    """User input and what to do with pressed keys."""

    def __init__(self):
        self.cur_key = 0
        self.nav = self.Navigation()
        self.quality = self.Quality()
        self.follow = self.Follow()
        self.request = self.Request()
        self.misc = self.Misc()

        self.keybinds = {
            config.cp["keys"]["back"]: self.nav.back,
            config.cp["keys"]["down"]: self.nav.down,
            config.cp["keys"]["forward"]: self.nav.forward,
            config.cp["keys"]["page+"]: self.nav.page_next,
            config.cp["keys"]["page-"]: self.nav.page_prev,
            config.cp["keys"]["up"]: self.nav.up,
            chr(curses.KEY_ENTER): self.nav.forward,
            chr(10): self.nav.forward,
            chr(13): self.nav.forward,
            config.cp["keys"]["qual+"]: self.quality.qual_next,
            config.cp["keys"]["qual-"]: self.quality.qual_prev,
            config.cp["keys"]["add"]: self.follow.add,
            config.cp["keys"]["delete"]: self.follow.delete,
            config.cp["keys"]["import"]: self.follow.user_import,
            config.cp["keys"]["followed"]: self.follow.follow_view,
            config.cp["keys"]["online"]: self.follow.follow_view,
            config.cp["keys"]["game"]: self.request.game_search,
            config.cp["keys"]["refresh"]: self.request.refresh,
            config.cp["keys"]["search"]: self.request.search,
            config.cp["keys"]["t_game"]: self.request.top_games_view,
            config.cp["keys"]["t_stream"]: self.request.top_streams_view,
            config.cp["keys"]["vods"]: self.request.vods_view,
            config.cp["keys"]["chat"]: self.misc.exec_chat,
            config.cp["keys"]["yank"]: self.misc.exec_yank,
            chr(curses.KEY_RESIZE): self.misc.resize,
        }

    def input(self):
        """Gets the pressed key, then calls the respective function."""
        self.cur_key = chr(ui.screen.getch())

        # Disable input while term is too small
        if ui.check_term_size() and self.cur_key != chr(curses.KEY_RESIZE):
            ui.donothing = True
            return

        if self.cur_key in self.keybinds:
            self.keybinds[self.cur_key]()
        else:
            ui.donothing = True

    class Navigation:
        """Keys used for moving the cursor and launching streamlink."""

        def down(self):
            """Move cursor down"""
            if ui.sel + ui.page * ui.maxitems + 1 < twitch.results:
                if ui.sel + 1 == ui.maxitems:
                    ui.page += 1
                    ui.sel = 0
                else:
                    ui.sel += 1

        def up(self):
            """Move cursor up"""
            if ui.sel == 0 and ui.page > 0:
                ui.page -= 1
                ui.sel = ui.maxitems - 1
            elif ui.sel > 0:
                ui.sel -= 1

        def forward(self):
            """Enter menu or launch stream"""
            if not ui.cur_page:
                return

            if ui.state in ("search", "vods") or (
                ui.state == "follow" and ui.f_filter == "online"
            ):
                ui.win_blink()
                if ui.state != "vods":
                    url = ui.cur_page[ui.sel]["channel"]["url"]
                else:
                    url = ui.cur_page[ui.sel]["url"]

                # streamlink expects the player to be a single quoted arg
                # change single quotes so they don't break shlex's splitting
                player = config.cp["exec"]["player"].replace("'", '"')
                quality = ui.quality[ui.cur_quality]

                # prefer 60fps streams, but fallback if they aren't available
                if quality[-1] == 'p':
                    quality = f"{quality}60,{quality}50,{quality}"

                cmd = (
                    f"setsid "  # detach process from terminal
                    f"{config.cp['exec']['streamlink']} -Q "
                    f"--http-header Client-ID={config.cp['twitch']['client_id']} "
                    f"-p '{player}' "
                    f"{url} {quality}"
                )

                Popen(shlex.split(cmd))

            elif ui.state == "top":
                twitch.request(["game", ui.cur_page[ui.sel]["game"]["name"]], "search")

        def back(self):
            """Go to cached page"""
            ui.state = twitch.state_cache
            twitch.data = twitch.cache
            twitch.set_results()
            ui.sel = ui.sel_cache
            ui.page = ui.page_cache

        def page_next(self):
            """Go to next page"""
            if twitch.results > (ui.page + 1) * ui.maxitems:
                ui.sel = 0
                ui.page += 1

        def page_prev(self):
            """Go to prev page"""
            if ui.page > 0:
                ui.sel = 0
                ui.page -= 1

    class Quality:
        """Keys used to select the quality of the stream."""

        def qual_next(self):
            """Select next highest quality"""
            if ui.cur_quality < len(ui.quality) - 1:
                ui.cur_quality += 1

        def qual_prev(self):
            """Select next lowest quality"""
            if ui.cur_quality > 0:
                ui.cur_quality -= 1

    class Follow:
        """Keys used to visit or interact with followed channels."""

        def follow_view(self):
            """Go to the followed channels page
            Or Toggle online/all follows"""
            if (user_input.cur_key == config.cp["keys"]["followed"] and ui.state != "follow") or (
                user_input.cur_key == config.cp["keys"]["online"] and ui.state == "follow" and ui.f_filter == "all"
            ):
                twitch.request(["channel", ",".join(config.followed.values())], "follow")
                ui.f_filter = "online"
            elif (user_input.cur_key == config.cp["keys"]["online"] and ui.state == "follow" and ui.f_filter == "online"):
                ui.f_filter = "all"

        def add(self):
            """Add a channel to the followed list
            Or show all followed channels
            """
            if not ui.cur_page:
                return

            if ui.state == "search":
                if ui.cur_page[ui.sel]["channel"]["name"] not in config.followed:
                    ui.win_blink()
                    config.followed[ui.cur_page[ui.sel]["channel"]["name"]] = str(
                        ui.cur_page[ui.sel]["channel"]["_id"]
                    )
            elif ui.state == "follow" and ui.f_filter != "all":
                ui.f_filter = "all"
                ui.reset_page()

        def delete(self):
            """Remove channel from followed list"""
            if ui.state != "follow":
                return

            if ui.f_filter == "all":
                ui.win_blink()
                if ui.cur_page:
                    del config.followed[ui.cur_page[ui.sel]]
            elif ui.f_filter == "online":
                if ui.cur_page:
                    del config.followed[ui.cur_page[ui.sel]["channel"]["name"]]
                    twitch.query = ["channel", ",".join(config.followed.values())]
                    user_input.request.refresh()

        def user_import(self):
            """Import follows from user"""
            if ui.state != "follow":
                return

            overwrite = False
            user = ui.prompt("Import from user")

            if user:
                config.import_follows_from_user(user, overwrite)
                twitch.query = ["channel", ",".join(config.followed.values())]
                user_input.request.refresh()

    class Request:
        """Keys used to query twitch"""

        def top_games_view(self):
            """Go to top games page"""
            twitch.request(["topgames", None], "top")

        def top_streams_view(self):
            """Go to top streams page"""
            twitch.request(["topstreams", " "], "search")

        def vods_view(self):
            """Go to vods page for channel"""
            if ui.state == "top" or not ui.cur_page:
                return

            if ui.state == "follow" and ui.f_filter == "all":
                twitch.request(["vods", str(config.followed[ui.cur_page[ui.sel]])], "vods")
            else:
                twitch.request(["vods", str(ui.cur_page[ui.sel]["channel"]["_id"])], "vods")

        def game_search(self):
            """Search by game name (exact match)"""
            string = ui.prompt("Enter Game")
            if string:
                twitch.request(["game", string.decode("utf-8")], "search")

        def search(self):
            """Search for streams"""
            string = ui.prompt("Enter Search Query")
            if string:
                twitch.request(["stream", string.decode("utf-8")], "search")

        def refresh(self):
            """Resend last request and reload results"""
            twitch.request()
            twitch.set_results()
            if twitch.data:
                if ui.state == twitch.state_cache:
                    twitch.cache = twitch.data
                if ui.sel >= twitch.results:
                    ui.sel = 0

    class Misc:
        """Keys that don't fit into the other categories."""

        def resize(self):
            """Reset the screen when the terminal is resized"""
            ui.init_screen()
            ui.reset_page(True)

        def exec_yank(self):
            """Yank channel url to clipboard"""
            if ui.state == "top" or not ui.cur_page:
                return

            ui.win_blink()
            if (ui.state == "search") or (ui.state == "follow" and ui.f_filter == "online"):
                clip = Popen(["xclip", "-selection", "c"], stdin=PIPE)
                clip.communicate(input=bytes(ui.cur_page[ui.sel]["channel"]["url"], "utf-8"))

        def exec_chat(self):
            """Open chat with chat_method"""
            if ui.state == "top" or not ui.cur_page:
                return

            if config.cp["exec"]["chat_method"] == "browser":
                cmd = (
                    f"{config.cp['exec']['browser']} "
                    f"https://twitch.tv/popout/{ui.cur_page[ui.sel]['channel']['name']}/chat"
                )

                Popen(shlex.split(cmd), stdout=DEVNULL, stderr=DEVNULL)
            elif config.cp["exec"]["chat_method"] == "weechat":
                network = config.cp["irc"]["network"]

                if config.cp.getboolean("irc", "no_account"):
                    num = randint(1000000, 99999999)
                    nicks = (
                        f"/set irc.server.{network}.nicks justinfan{num};"
                        f"/set irc.server.{network}.username justinfan{num};"
                        f"/set irc.server.{network}.realname justinfan{num};"
                    )
                else:
                    nicks = ""

                cmd = (
                    f"{config.cp['exec']['term']} "
                    "weechat -r '"
                    f"/server add {network} "
                    f"{config.cp['irc']['address']}/{config.cp['irc']['port']};"
                    f"/set irc.server.{network}.command "
                    "/quote CAP REQ :twitch.tv/membership;"
                    f"/set irc.server.{network}.ssl on;"
                    f"{nicks}"
                    # Setting autojoin is kind of hacky
                    # It will overwrite the saved setting for the network
                    # TODO Alternatives for cleaner joining?
                    f"/set irc.server.{network}.autojoin "
                    f"#{ui.cur_page[ui.sel]['channel']['name']};"
                    f"/connect {network}'"
                )

                Popen(shlex.split(cmd))
            elif config.cp["exec"]["chat_method"] == "irssi":
                # Irssi doesn't seem to support running commands from args
                # And editing irssi's config file itself seems messy
                # The best we could do is join an existing network
                # and copy the join command to clipboard
                cmd = f"{config.cp['exec']['term']} irssi -c {config.cp['irc']['network']}"

                Popen(shlex.split(cmd))

                clip = Popen(["xclip", "-selection", "c"], stdin=PIPE)
                clip.communicate(
                    input=bytes("/join #" + ui.cur_page[ui.sel]["channel"]["name"], "utf-8")
                )


class Query:
    """Make requests to Twitch and store results."""

    def __init__(self):
        self.cache = []
        self.data = []
        self.query = ["topgames", None]
        self.results_limit = config.cp.getint("twitch", "results_limit")
        self.retry_limit = config.cp.getint("twitch", "retry_limit")
        self.results = 0
        self.state_cache = "top"
        self.url = ""

    def request(self, req=None, state=None):
        """Fire off request and set data json. Optionally sets the state.
        Retry up to X times on fail."""

        if ui and self.cache:
            ui.win_blink()

        self.prep_url(req)

        for _ in range(self.retry_limit):
            try:
                headers = {
                    "Accept": "application/vnd.twitchtv.v5+json",
                    "Client-ID": config.cp["twitch"]["client_id"],
                }
                ret = requests.get(self.url, headers=headers, timeout=5)
                if ret.status_code != 200:
                    continue

                try:
                    self.cache = self.data
                    self.data = ret.json()
                    if ui:
                        self.state_cache = ui.state
                        if state:
                            ui.set_state(state)
                    return
                except ValueError:
                    self.data = None
            except requests.exceptions.RequestException:
                sleep(3)
        self.data = None

    def prep_url(self, req=None):
        """Prepares the url for the request. Defaults to last request made"""
        if req:
            self.query = req
            if req[1]:
                req[1] = quote(req[1])
        else:
            req = self.query

        url = "https://api.twitch.tv/kraken/"

        if req[0] == "topgames":
            url += f"games/top?limit={self.results_limit}"
        elif req[0] == "topstreams":
            url += f"streams?limit={self.results_limit}"
        elif req[0] == "game":
            url += f"streams?limit={self.results_limit}&game={req[1]}"
            if config.cp["twitch"]["lang"] != "":
                url += f"&language={config.cp['twitch']['lang']}"
        elif req[0] == "channel":
            url += f"streams/?channel={req[1]}"
        elif req[0] == "stream":
            url += f"search/streams?limit={self.results_limit}&query={req[1]}"
        elif req[0] == "vods":
            url += f"channels/{req[1]}/videos?limit={self.results_limit}"
        elif req[0] == "get_id":
            url += f"users?login={req[1]}"
        elif req[0] == "get_follows":
            url += f"users/{req[1]}/follows/channels?limit={self.results_limit}"
        else:
            raise ValueError("Invalid Type Passed")

        self.url = url

    def set_results(self):
        """Count the number of results from the request."""
        if self.data:
            if ui.state == "top":
                self.results = len(self.data["top"])
            elif (ui.state == "search") or (ui.state == "follow" and ui.f_filter == "online"):
                self.results = len(self.data["streams"])
            elif ui.state == "follow" and ui.f_filter == "all":
                self.results = len(config.followed)
            elif ui.state == "vods":
                self.results = len(self.data["videos"])
        else:
            self.results = 0

    def get_twitch_id(self, name):
        """Takes a twitch channel username, Returns its corresponding ID"""
        self.request(["get_id", name])
        if self.data["_total"] > 0:
            return self.data["users"][0]["_id"]

    def get_default_view(self):
        """Request for default view on program start"""
        default_view = config.cp["ui"]["default_state"]
        if default_view == "games":
            self.request(["topgames", None], "top")
        elif default_view == "followed":
            self.request(["channel", ",".join(config.followed.values())], "follow")
        elif default_view == "streams":
            self.request(["stream", " "], "search")
        else:
            raise ValueError("Config Error: default_state is invalid")

        self.cache = self.data
        self.state_cache = ui.state


class CLI:
    """Commands to be run without the TUI interface"""

    def __init__(self):
        self.arg_num = len(sys.argv)
        self.cur_arg = sys.argv[1]

        self.commands = {
            "-a": self.add_user_follow,
            "-d": self.delete_user_follow,
            "-f": self.get_online_followed,
            "-h": self.display_help,
            "--help": self.display_help,
            "-i": self.import_user_follows,
            "-v": self.version,
        }

    def arg_run(self):
        """Gets the passed arg, then calls the respective function."""

        if self.cur_arg in self.commands:
            self.commands[self.cur_arg]()
        else:
            print(f"Invalid Argument Passed: {self.cur_arg}")

    def display_help(self):
        """Prints help to the screen"""
        print(
            """reflex-curses [OPTION]

OPTIONS
       NONE   Starts up the tui interface

       -a channel_name
              Add a twitch channel to your followed list

       -d channel_name
              Delete a twitch channel from your followed list

       -f     Prints out any followed streams that are online.

       -h, --help
              Print help message

       -i channel_name (--overwrite)
              Import channels followed by channel_name into your followed list.
              Default is to append to your current followed list, add --overwrite to replace it.
              NOTE: Currently limited to the results_limit (default: 75), large followed lists
                    might not fully import.

       -v     Print version
        """
        )

    def add_user_follow(self):
        """Adds a channel name to your followed list"""
        if self.arg_num != 3:
            print("Usage: reflex-curses -a channel_name")
            return

        if sys.argv[2] in config.followed:
            print(f"Channel {sys.argv[2]} already followed")
            return

        user_id = twitch.get_twitch_id(sys.argv[2])

        if not user_id:
            print(f"Channel {sys.argv[2]} not found")
            return

        config.followed[sys.argv[2]] = user_id
        print(f"Followed {sys.argv[2]}")
        config.write_followed_list()

    def delete_user_follow(self):
        """Deletes a channel from your followed list"""
        if self.arg_num != 3:
            print("Usage: reflex-curses -d channel_name")
            return

        if sys.argv[2] not in config.followed:
            print(f"Channel {sys.argv[2]} not followed")
            return

        del config.followed[sys.argv[2]]
        print(f"Deleted {sys.argv[2]}")
        config.write_followed_list()

    def get_online_followed(self):
        """Prints any online streams in the followed list"""
        twitch.request(["channel", ",".join(config.followed.values())])
        if twitch.data:
            for stream in sorted(
                twitch.data["streams"], key=lambda i: str(i["channel"]["display_name"]).lower(),
            ):
                print(stream["channel"]["display_name"])

    def import_user_follows(self):
        """Adds twitch user's follow list to your own"""
        if self.arg_num not in (3, 4):
            print("Usage: reflex-curses -i channel_name (--overwrite)")
            return

        overwrite = bool(self.arg_num == 4 and sys.argv[3] == "--overwrite")

        if overwrite:
            old_follows = 0
        else:
            old_follows = len(config.followed)

        config.import_follows_from_user(sys.argv[2], overwrite)

        if twitch.data:
            print(f"Imported {len(config.followed) - old_follows} new follows.")
            config.write_followed_list()
        else:
            print(f"Followed list for {sys.argv[2]} not found.")

    def version(self):
        """Prints version number"""
        print(f"{VERSION}")


def main():
    try:
        twitch.get_default_view()

        while user_input.cur_key != config.cp["keys"]["quit"]:

            if ui.donothing:
                ui.donothing = False
            else:
                ui.set_cur_page()
                twitch.set_results()

                if ui.check_term_size():
                    ui.warn_term_size()
                else:
                    ui.draw_win_l()
                    ui.draw_win_r()

            user_input.input()
    finally:
        curses.nocbreak()
        ui.screen.keypad(0)
        curses.echo()
        curses.endwin()
        config.write_config()
        config.write_followed_list()


# Class Inits
config = Config()
twitch = Query()
ui = None  # Dummy init for cli invocation

config.init_followed_list()

if len(sys.argv) >= 2:
    cli = CLI()
    cli.arg_run()
    sys.exit()

ui = Interface()
user_input = Keybinds()

if __name__ == "__main__":
    main()
