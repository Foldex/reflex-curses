#!/usr/bin/env python

import configparser
import curses
import sys
from os import path, makedirs
from random import randint
from shutil import copyfile
from subprocess import Popen, PIPE, DEVNULL
from textwrap import wrap
from time import sleep
from urllib.parse import quote, unquote

import requests


class Config:
    """Configuration Variables and Locally Followed Twitch Channels."""

    def __init__(self):
        self.config_dir = path.expanduser("~/.config/reflex-curses")
        self.followed = {}
        self.cp = configparser.ConfigParser()

        # TODO Move followedlist over to configparser?
        self.init_followed_list()

        # Setup Default Values
        self.cp["keys"] = {
            "add": 'a',       # Add a channel to the followed list
                              # If in followed view, show all streams
            "chat": 'c',      # Open chat with chat_method
            "delete": 'd',    # Delete channel from followed list
            "followed": 'f',  # Switch to followed view
            "game": 'g',      # Search by Game Name (exact)
            "back": 'h',      # Go to initial view
            "down": 'j',      # Move cursor down
            "up": 'k',        # Move cursor up
            "forward": 'l',   # Enter menu or launch stream
            "online": 'o',    # Show only online streams in followed list
            "quit": 'q',      # Quit
            "refresh": 'r',   # Resend last query
            "t_stream": 's',  # Go to top streams view
            "t_game": 't',    # Go to top games view
            "search": '/',    # Search for streams
            "vods": 'v',      # Go to VOD view
            "yank": 'y',      # Yank channel url
            "page+": 'n',     # Next Page
            "page-": 'p',     # Previous page
            "qual+": '=',     # Select higher quality
            "qual-": '-'      # Select lower quality
        }

        self.cp["exec"] = {
            "browser": "firefox",
            "browser_flag": "--new-window",
            "chat_method": "browser",  # browser/weechat/irc
            "player": "mpv",
            "term": "urxvt",
            "term_flag": "-e"
        }

        self.cp["twitch"] = {
            "client_id": "caozjg12y6hjop39wx996mxn585yqyk",
            "lang": "",           # Language filter
            # API limit is 100, but API seems to choke at higher than 75
            "results_limit": 75,  # Max number of results for a query
            "retry_limit": 3      # Max number of retries for a query
        }

        self.cp["ui"] = {
            # Supported Colors:
            # black/blue/cyan/green/magenta/white/yellow/red
            "default_state": "games",  # Initial view: games/followed/streams
            "hl_color": "blue",        # Color of selected item highlight
            "l_win_color": "white",    # Color of left window
            "r_win_color": "green",    # Color of right window
            "quality": "best",         # Default quality selection
            "show_keys": "True"        # Display Keybinds
        }

        self.cp["irc"] = {
            "address": "irc.chat.twitch.tv",  # Address of the irc server
            "network": "reflex",              # Name of the saved network
            "port": "6697"                    # Port of the irc server
        }

        # Read in Config File
        self.cp.read(self.config_dir + "/config")

    def write_config(self):
        """Writes config to file"""
        with open(self.config_dir + "/config", 'w') as configfile:
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

    def write_followed_list(self):
        """Write followed channels list to file, backing up old one."""
        file_path = f"{self.config_dir}/followed"
        self.backup(file_path)

        file = open(file_path, 'w')
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
                "red": curses.COLOR_RED
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

        self.quality = ["audio_only", "worst", "360p", "480p", "720p", "best"]
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
        """Initializes screen and displays logo.
        Is also called when the terminal is resized.
        """
        self.screen.clear()
        self.size = self.screen.getmaxyx()
        if self.check_term_size():
            return
        self.maxlen = self.size[1] // 2 - 4
        self.maxitems = self.size[0] // 2 - 1
        self.win_l = curses.newwin(self.size[0], self.size[1] // 2, 0, 0)
        self.win_r = curses.newwin(self.size[0], self.size[1] // 2, 0,
                                   self.size[1] // 2)

        if self.size[1] > 90:
            logo = (
                "            __ _                                               \n"
                "  _ __ ___ / _| | _____  __      ___ _   _ _ __ ___  ___  ___  \n"
                " | '__/ _ \\ |_| |/ _ \\ \\/ /____ / __| | | | '__/ __|/ _ \\/ __| \n"
                " | | |  __/  _| |  __/>  <_____| (__| |_| | |  \\__ \\  __/\\__ \\ \n"
                " |_|  \\___|_| |_|\\___/_/\\_\\     \\___|\\__,_|_|  |___/\\___||___/ \n")
            logo_height = len(logo.splitlines()) + 1
            for i, line in enumerate(logo.splitlines(), 2):
                self.screen.addnstr(self.size[0] // 2 - (logo_height - i),
                                    self.size[1] // 2 - (len(line) // 2),
                                    line, self.maxlen, self.hl_2)

        else:
            self.screen.addnstr(self.size[0] // 2 - 1,
                                self.size[1] // 2 - 5,
                                "Loading...",
                                self.maxlen)

        self.screen.move(0, 0)
        self.screen.refresh()

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
                self.cur_page = twitch.data['top'][start:end]
            elif (self.state == "search") or (
                    self.state == 'follow' and self.f_filter == 'online'):
                self.cur_page = twitch.data['streams'][start:end]
            elif self.state == "follow" and self.f_filter == "all":
                self.cur_page = list(config.followed)[start:end]
            elif self.state == "vods":
                self.cur_page = twitch.data['videos'][start:end]
        else:
            self.cur_page = []

    def prompt(self, text):
        """Prompt user for text input in new popup window, return the text.
        If nothing was entered, kill the window.
        Used for searching for streams and game name.
        """
        win = curses.newwin(3, self.size[1] // 2 - 4,
                            self.size[0] // 2 - 1, self.size[1] // 4)
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
        self.win_l.border(0)
        self.win_l.addnstr(self.size[0] - 1,
                           self.size[1] // 2 - 9,
                           f"page:{self.page + 1}",
                           self.maxlen)
        index = 0

        for i in self.cur_page:
            if index < self.maxitems:
                if self.state == "top":
                    string = str(i['game']['name'])
                elif self.state == "vods":
                    string = str(i['title']).replace("\n", "")
                    # truncate long vod titles
                    if len(string) > self.maxlen // 2:
                        string = string[:self.maxlen // 2] + "..."
                    string += " - " + str(i['game'])
                elif (self.state == "search" or (
                        self.state == "follow" and self.f_filter == "online")):
                    string = str(i['channel']['display_name'])
                    if twitch.query[0] != "game":
                        string += " - " + str(i['game'])
                elif self.state == "follow" and self.f_filter == "all":
                    string = str(i)

                if index == self.sel:
                    self.win_l.addnstr(index * 2 + 2, 2,
                                       string, self.maxlen,
                                       curses.A_UNDERLINE | self.hl_1)
                else:
                    self.win_l.addnstr(index * 2 + 2, 2,
                                       string, self.maxlen, self.hl_3)
            index += 1

        # Headers
        if self.state == "search" and twitch.query[0] == "game":
            text = unquote(twitch.query[1])
            t_len = len(text)
            self.win_l.addnstr(1, self.size[1] // 2 - (t_len + 2),
                               text,
                               self.maxlen)
            self.win_l.hline(2, self.size[1] // 2 - (t_len + 2),
                             curses.ACS_HLINE, t_len)
        elif self.state == "vods":
            text = "VODs"
            t_len = len(text)
            self.win_l.addnstr(1, self.size[1] // 2 - (t_len + 2),
                               text,
                               self.maxlen)
            self.win_l.hline(2, self.size[1] // 2 - (t_len + 2),
                             curses.ACS_HLINE, t_len)

        self.win_l.refresh()

    def draw_win_r(self):
        """Display right half of the screen.
        Right window is used for displaying additional info like descriptions.
        """
        self.win_r.erase()
        self.win_r.border(0)
        self.draw_keys()
        index = 0

        for i in self.cur_page:
            if index < self.maxitems:
                if index == self.sel:
                    if self.state == "top":
                        self.win_r.addnstr(2, 3,
                                           f"Viewers: {i['viewers']}",
                                           self.maxlen, self.hl_2)
                        self.win_r.addnstr(3, 3,
                                           f"Channels: {i['channels']}",
                                           self.maxlen, self.hl_2)
                    elif self.state == "vods":
                        m, s = divmod(i['length'], 60)
                        h, m = divmod(m, 60)

                        self.win_r.addnstr(2, 3,
                                           f"Date: {i['created_at']}",
                                           self.maxlen, self.hl_2)
                        self.win_r.addnstr(3, 3,
                                           f"Views: {i['views']}",
                                           self.maxlen, self.hl_2)
                        self.win_r.addnstr(4, 3,
                                           f"Length: {h:02}:{m:02}:{s:02}",
                                           self.maxlen, self.hl_2)
                        self.win_r.addnstr(5, 3,
                                           f"Status: {i['status']}",
                                           self.maxlen, self.hl_2)
                    elif (self.state == "search" or
                          (self.state == "follow" and
                           self.f_filter == "online")):
                        self.win_r.addnstr(
                            self.size[0] - 3, 2,
                            "quality: " +
                            config.cp["keys"]['qual-'] +
                            config.cp["keys"]['qual+'],
                            self.maxlen)
                        self.win_r.addnstr(self.size[0] - 2, 3,
                                           self.quality[self.cur_quality],
                                           self.maxlen)
                        self.win_r.addnstr(2, 3,
                                           str(i['channel']['url']),
                                           self.maxlen, self.hl_2)
                        self.win_r.addnstr(4, 3,
                                           f"Language: {i['channel']['language']}",
                                           self.maxlen, self.hl_2)
                        self.win_r.addnstr(5, 3,
                                           f"Viewers: {i['viewers']}",
                                           self.maxlen, self.hl_2)
                        self.win_r.addnstr(6, 3,
                                           "Status:",
                                           self.maxlen, self.hl_2)
                        status = wrap(str(i['channel']['status']),
                                      self.size[1] // 2 - 6)
                        l_num = 7
                        for line in status:
                            if l_num >= self.size[0] - 4:
                                break
                            self.win_r.addstr(l_num, 4,
                                              line,
                                              self.hl_2)
                            l_num += 1
                        # TODO Clean up
                        # Lazy way of setting cursor position to display stderr
                        # output from streamlink. A large enough error message
                        # will vomit on the screen
                        self.win_r.addstr(l_num, 4,
                                          "",
                                          self.hl_2)
            index += 1

        self.win_r.refresh()

    def draw_keys(self):
        """Displays keybinds for each page in the right hand window."""
        if not config.cp.getboolean("ui", "show_keys"):
            return

        items = [
            "search: " + config.cp["keys"]["search"],
            "followed: " + config.cp["keys"]["followed"],
            "game: " + config.cp["keys"]["game"],
            "refresh: " + config.cp["keys"]["refresh"],
            "quit: " + config.cp["keys"]["quit"]
        ]

        # TODO Cleanup
        if self.state == "follow":
            del items[1]
            items.insert(1, f"delete: {config.cp['keys']['delete']}")
            if self.f_filter == "online":
                items.insert(1, f"all: {config.cp['keys']['add']}")
            elif self.f_filter == "all":
                items.insert(1, f"online: {config.cp['keys']['online']}")
        elif self.state == "search":
            items.insert(1, f"add follow: {config.cp['keys']['add']}")

        if self.state != "top":
            items.insert(2, f"chat: {config.cp['keys']['chat']}")
            items.insert(len(items) - 1, f"top streams: {config.cp['keys']['t_stream']}")
            items.insert(len(items) - 1, f"top games: {config.cp['keys']['t_game']}")
            items.insert(len(items) - 1, f"vods: {config.cp['keys']['vods']}")
            items.insert(len(items) - 1, f"yank: {config.cp['keys']['yank']}")
            items.insert(0, f"back: {config.cp['keys']['back']}")

        length = len(items)

        # only draw keys if it takes up less than half the vertical space
        if self.size[0] // 2 > length:
            for i in items:
                self.win_r.addnstr(self.size[0] - (length + 1),
                                   self.size[1] // 2 - (len(i) + 2),
                                   i, self.maxlen)
                length -= 1


class Keybinds:
    """User input and what to do with pressed keys."""

    # FIXME Crash on 0 results queries with some keybinds

    def __init__(self):
        self.cur_key = 0
        self.keybinds = {
            config.cp["keys"]["add"]: self.follow_keys,
            config.cp["keys"]["delete"]: self.follow_keys,
            config.cp["keys"]["followed"]: self.follow_keys,
            config.cp["keys"]["game"]: self.query_keys,
            config.cp["keys"]["back"]: self.move_keys,
            config.cp["keys"]["down"]: self.move_keys,
            config.cp["keys"]["up"]: self.move_keys,
            config.cp["keys"]["forward"]: self.move_keys,
            config.cp["keys"]["online"]: self.follow_keys,
            config.cp["keys"]["refresh"]: self.query_keys,
            config.cp["keys"]["search"]: self.query_keys,
            config.cp["keys"]["t_stream"]: self.query_keys,
            config.cp["keys"]["t_game"]: self.query_keys,
            config.cp["keys"]["vods"]: self.query_keys,
            config.cp["keys"]["page-"]: self.move_keys,
            config.cp["keys"]["page+"]: self.move_keys,
            config.cp["keys"]["qual-"]: self.qual_keys,
            config.cp["keys"]["qual+"]: self.qual_keys,
            config.cp["keys"]["chat"]: self.misc_keys,
            config.cp["keys"]["yank"]: self.misc_keys,
            chr(curses.KEY_ENTER): self.move_keys,
            chr(curses.KEY_RESIZE): self.misc_keys
        }

    def input(self):
        """Gets the pressed key, then calls the respective function."""
        # TODO Cleanup
        self.cur_key = chr(ui.screen.getch())

        # Disable input while term is too small
        if ui.check_term_size() and self.cur_key != chr(curses.KEY_RESIZE):
            ui.donothing = True
            return

        if self.cur_key in self.keybinds:
            self.keybinds[self.cur_key]()
        else:
            ui.donothing = True

    def move_keys(self):
        """Keys used for moving the cursor and launching streamlink."""
        if self.cur_key == config.cp["keys"]["down"]:
            if ui.sel + ui.page * ui.maxitems + 1 < twitch.results:
                if ui.sel + 1 == ui.maxitems:
                    ui.page += 1
                    ui.sel = 0
                else:
                    ui.sel += 1
        elif self.cur_key == config.cp["keys"]["up"]:
            if ui.sel == 0 and ui.page > 0:
                ui.page -= 1
                ui.sel = ui.maxitems - 1
            elif ui.sel > 0:
                ui.sel -= 1
        elif self.cur_key in (config.cp["keys"]["forward"],
                              chr(curses.KEY_ENTER)):
            if (ui.state in ("search", "vods") or (
                    ui.state == "follow" and ui.f_filter == "online")):
                ui.win_blink()
                if ui.state != "vods":
                    url = ui.cur_page[ui.sel]['channel']['url']
                else:
                    url = ui.cur_page[ui.sel]['url']

                Popen([
                    "setsid",  # don't close mpv if reflex is closed
                    "streamlink",
                    "-Q", "--twitch-disable-hosting",
                    "--http-header",
                    "Client-ID=" + config.cp["twitch"]["client_id"],
                    "-t {author} - {title}",
                    "-p", config.cp["exec"]["player"],
                    url, ui.quality[ui.cur_quality]])
            elif ui.state == "top":
                ui.win_blink()
                twitch.request(["game",
                                ui.cur_page[ui.sel]['game']['name']],
                               "search")
        elif self.cur_key == config.cp["keys"]["back"]:
            ui.state = twitch.state_cache
            twitch.data = twitch.cache
            twitch.set_results()
            ui.sel = ui.sel_cache
            ui.page = ui.page_cache
        elif (self.cur_key == config.cp["keys"]["page+"] and
              twitch.results > (ui.page + 1) * ui.maxitems):
            ui.sel = 0
            ui.page += 1
        elif self.cur_key == config.cp["keys"]["page-"] and ui.page > 0:
            ui.sel = 0
            ui.page -= 1

    def qual_keys(self):
        """Keys used to select the quality of the stream."""
        if self.cur_key == config.cp["keys"]["qual-"] and ui.cur_quality > 0:
            ui.cur_quality -= 1
        elif (self.cur_key == config.cp["keys"]["qual+"] and
              ui.cur_quality < len(ui.quality) - 1):
            ui.cur_quality += 1

    def follow_keys(self):
        """Keys used to visit or interact with followed channels."""
        if self.cur_key == config.cp["keys"]["add"]:
            if ui.state == "search":
                if ui.cur_page[ui.sel]['channel']['name'] not in config.followed:
                    ui.win_blink()
                    config.followed[ui.cur_page[ui.sel]['channel']['name']] = str(
                        ui.cur_page[ui.sel]['channel']['_id'])
            elif ui.state == "follow" and ui.f_filter != "all":
                ui.f_filter = "all"
                ui.reset_page()
        elif (self.cur_key == config.cp["keys"]["followed"] and ui.state != "follow") or (
                self.cur_key == config.cp["keys"]["online"] and ui.f_filter == "all"):
            ui.win_blink()
            twitch.request(["channel",
                            ",".join(config.followed.values())],
                           "follow")
            ui.f_filter = "online"
        elif self.cur_key == config.cp["keys"]["delete"] and ui.state == "follow":
            if ui.f_filter == "all":
                ui.win_blink()
                if ui.cur_page:
                    del config.followed[ui.cur_page[ui.sel]]
            elif ui.f_filter == "online":
                ui.win_blink()
                if ui.cur_page:
                    del config.followed[ui.cur_page[ui.sel]
                                        ['channel']['name']]
                    ui.win_blink()
                    twitch.query = [
                        "channel", ",".join(
                            config.followed.values())]
                    self.cur_key = config.cp["keys"]["refresh"]
                    self.query_keys()

    def query_keys(self):
        """Keys used to query twitch"""
        if self.cur_key == config.cp["keys"]["search"]:
            string = ui.prompt("Enter Search Query")
            if string:
                ui.win_blink()
                twitch.request(["stream", string.decode("utf-8")], "search")
        elif self.cur_key == config.cp["keys"]["t_game"]:
            ui.win_blink()
            twitch.request(["topgames", None], "top")
        elif self.cur_key == config.cp["keys"]["t_stream"]:
            ui.win_blink()
            twitch.request(["stream", " "], "search")
        elif self.cur_key == config.cp["keys"]["game"]:
            string = ui.prompt("Enter Game")
            if string:
                ui.win_blink()
                twitch.request(["game", string.decode("utf-8")], "search")
        elif self.cur_key == config.cp["keys"]["vods"]:
            if ui.state != "top":
                if ui.state == "follow" and ui.f_filter == "all":
                    twitch.request(["vods",
                                    str(config.followed[ui.cur_page[ui.sel]])],
                                   "vods")
                else:
                    twitch.request(["vods",
                                    str(ui.cur_page[ui.sel]['channel']['_id'])],
                                   "vods")
        elif self.cur_key == config.cp["keys"]["refresh"]:
            ui.win_blink()
            twitch.request()
            twitch.set_results()
            if twitch.data:
                if ui.state == twitch.state_cache:
                    twitch.cache = twitch.data
                if ui.sel >= twitch.results:
                    ui.sel = 0

    def misc_keys(self):
        """Keys that don't fit into the other categories."""
        if self.cur_key == chr(curses.KEY_RESIZE):
            ui.init_screen()
            ui.reset_page(True)
        elif self.cur_key == config.cp["keys"]['chat'] and ui.state != "top":
            if config.cp["exec"]["chat_method"] == "browser":
                Popen([config.cp["exec"]["browser"],
                       config.cp["exec"]["browser_flag"],
                       ("https://twitch.tv/popout/"
                        f"{ui.cur_page[ui.sel]['channel']['name']}/chat")],
                      stdout=DEVNULL, stderr=DEVNULL)
            elif config.cp["exec"]["chat_method"] == "weechat":
                # TODO Allow login via account oauth
                num = randint(1000000, 99999999)
                nick = f"justinfan{num}"
                Popen([config.cp["exec"]["term"],
                       config.cp["exec"]["term_flag"],
                       'weechat', '-r',
                       (f'/server add {config.cp["irc"]["network"]} '
                        f'{config.cp["irc"]["address"]}/{config.cp["irc"]["port"]};'
                        '/set irc.server.{config.cp["irc"]["network"]}.command '
                        '/quote CAP REQ :twitch.tv/membership;'
                        f'/set irc.server.{config.cp["irc"]["network"]}.nicks {nick};'
                        f'/set irc.server.{config.cp["irc"]["network"]}.username {nick};'
                        f'/set irc.server.{config.cp["irc"]["network"]}.realname {nick};'
                        # Setting autojoin is kind of hacky
                        # It will overwrite the saved setting for the network
                        # TODO Alternatives for cleaner joining?
                        f'/set irc.server.{config.cp["irc"]["network"]}.autojoin '
                        f'#{ui.cur_page[ui.sel]["channel"]["name"]};'
                        f'/connect {config.cp["irc"]["network"]}')])
            elif config.cp["exec"]["chat_method"] == "irssi":
                # Irssi doesn't seem to support running commands from args
                # And editing irssi's config file itself seems messy
                # The best we could do is join an existing network
                # and copy the join command to clipboard
                Popen([config.cp["exec"]["term"],
                       config.cp["exec"]["term_flag"],
                       'irssi', '-c', config.cp["irc"]["network"]])
                clip = Popen(['xclip', '-selection', 'c'], stdin=PIPE)
                clip.communicate(input=bytes(
                    "/join #" + ui.cur_page[ui.sel]['channel']['name'], 'utf-8'))
        elif self.cur_key == config.cp["keys"]['yank']:
            ui.win_blink()
            # copy channel url to clipboard
            if (ui.state == "search") or (
                    ui.state == 'follow' and ui.f_filter == 'online'):
                clip = Popen(['xclip', '-selection', 'c'], stdin=PIPE)
                clip.communicate(input=bytes(
                    ui.cur_page[ui.sel]['channel']['url'], 'utf-8'))


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

    def request(self, req=None, state=None):
        """Fire off request and set data json. Defaults to last request made.
        Optionally sets the state.
        Retry up to X times on fail."""

        if req:
            self.query = req
            if req[1]:
                req[1] = quote(req[1])
        else:
            req = self.query

        url = "https://api.twitch.tv/kraken/"

        if req[0] == "topgames":
            url += f"games/top?limit={self.results_limit}"
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
        else:
            raise ValueError("Invalid Type Passed")

        # TODO Cleanup
        for i in range(self.retry_limit):
            try:
                headers = {
                    "Accept": "application/vnd.twitchtv.v5+json",
                    "Client-ID": config.cp["twitch"]["client_id"],
                }
                ret = requests.get(url, headers=headers, timeout=5)
                if ret.status_code == 200:
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

    def set_results(self):
        """Count the number of results from the request."""
        if self.data:
            if ui.state == "top":
                self.results = len(self.data['top'])
            elif (ui.state == "search") or (
                    ui.state == 'follow' and ui.f_filter == 'online'):
                self.results = len(self.data['streams'])
            elif ui.state == "follow" and ui.f_filter == "all":
                self.results = len(config.followed)
            elif ui.state == "vods":
                self.results = len(self.data['videos'])
        else:
            self.results = 0

    def get_twitch_id(self, name):
        """Takes a twitch channel username, Returns its corresponding ID"""
        self.request(["get_id", name])
        if self.data['_total'] > 0:
            return self.data['users'][0]['_id']

    def get_default_view(self):
        """Request for default view on program start"""
        default_view = config.cp["ui"]["default_state"]
        if default_view == "games":
            self.request(["topgames", None], "top")
        elif default_view == "followed":
            self.request(["channel",
                          ",".join(config.followed.values())],
                         "follow")
        elif default_view == "streams":
            self.request(["stream", " "], "search")
        else:
            raise ValueError("Config Error: default_state is invalid")

        self.cache = self.data
        self.state_cache = ui.state


if __name__ == '__main__':

    config = Config()
    twitch = Query()
    ui = None  # Dummy init for cli invocation

    if len(sys.argv) >= 2:

        if sys.argv[1] == "-f":
            twitch.request(["channel", ",".join(config.followed.values())],
                           "follow")
            if twitch.data:
                for stream in sorted(twitch.data["streams"],
                                     key=lambda i: str(i['channel']['display_name']).lower()):
                    print(stream['channel']['display_name'])

        sys.exit()

    ui = Interface()
    user_input = Keybinds()

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
