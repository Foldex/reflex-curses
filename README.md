<p align="center">
  <img src="/reflex.png" title="reflex-curses"/>
</p>

- [Description](#orgb8169a5)
- [Changes](#org1bc8f9b)
- [Dependencies](#orgf44b078)
  - [Python](#org88c3222)
  - [External](#orgdad08ea)
  - [Optional](#org21b258a)
- [Default Keybinds](#org348d4f4)
- [Configuration](#orgab3d14f)
  - [Config File](#org687f105)
  - [Followed List Import](#org6d89dec)



<a id="orgb8169a5"></a>

# Description

Reflex-Curses is a fork of [twitch-curses](https://gitlab.com/corbie/twitch-curses) with added features.


<a id="org1bc8f9b"></a>

# Changes

-   Rewritten with classes
-   Launch multiple streams at once
-   Stream process no longer tied to terminal (setsid)
-   Launch chat for selected stream (browser/weechat/irssi)
-   Copy channel URL to clipboard (xclip)
-   Locally follow channels (No account needed) (+ Batch Imports from list)
-   Custom Config File
-   VOD Support
-   Search by game name
-   Top streams view
-   Language filter (Game search only)
-   Vim like keybinds
-   Updated to Twitch v5 API
-   Color support
-   Fixed crashing with super small terminal resizing


<a id="orgf44b078"></a>

# Dependencies


<a id="org88c3222"></a>

## Python

-   Python 3.6
-   python-requests


<a id="orgdad08ea"></a>

## External

-   streamlink (launching streams)
-   mpv (default player)
-   xclip (clipboard support)
-   urxvt (default terminal)
-   setsid (detach player from terminal)


<a id="org21b258a"></a>

## Optional

-   firefox (default browser)
-   weechat / irssi (chat)


<a id="org348d4f4"></a>

# Default Keybinds

| Key       | Description                               |
|--------- |----------------------------------------- |
| h         | Go to initial view                        |
| j         | Move cursor down                          |
| k         | Move cursor up                            |
| l / Enter | Enter menu or launch stream               |
| n         | Next Page                                 |
| p         | Previous page                             |
| f         | Switch to followed view                   |
| t         | Go to top games view                      |
| v         | Go to VOD view                            |
| g         | Search by Game Name (exact)               |
| -         | Decrease quality                          |
| =         | Increase quality                          |
| a         | Add a channel to the followed list        |
|           | If in Followed list, show all streams     |
| d         | Delete channel from followed list         |
| o         | Show only online streams in followed list |
| c         | Open chat with chat method                |
| y         | Yank channel url                          |
| r         | Refresh last query                        |
| q         | Quit                                      |


<a id="orgab3d14f"></a>

# Configuration

Configuration files are stored in ```~/.config/reflex-curses```


<a id="org687f105"></a>

## Config File

Config file is stored in ```~/config/reflex-curses/config```

Commented Config Example:

```
[keys]
# Add a channel to the followed list
# If in followed view, show all streams
add = a
# Open chat with chat_method
chat = c
# Delete channel from followed list
delete = d
# Switch to followed view
followed = f
# Search by Game Name (exact)
game = g
# Go to initial view
back = h
# Move cursor down
down = j
# Move cursor up
up = k
# Enter menu or launch stream
forward = l
# Show only online streams in followed list
online = o
# quit
quit = q
# resend last query
refresh = r
# go to top games view
top = t
# search for streams
search = /
# Go to VOD view
vods = v
# Yank channel url
yank = y
# Next Page
page+ = n
# Previous page
page- = p
# Select higher quality
qual+ = =
# Select lower quality
qual- = -

[exec]
# browser to open chat in
browser = firefox
# single arg to pass to browser
browser_flag = --new-window
# browser/weechat/irc
chat_method = browser
# default player
player = mpv
# default terminal
term = urxvt
# single arg to pass to term
term_flag = -e

[twitch]
# twitch client id used for API requests
client_id = caozjg12y6hjop39wx996mxn585yqyk
# language filter (Empty means all)
lang =
# maximum amount of results (API limit is 100, but API seems to choke at higher than 75)
query_limit = 75
# maximum amount of times to retry a failed request
retry_limit = 3

[ui]
# Supported Colors:
# black/blue/cyan/green/magenta/white/yellow/red

# currently selected item highlight color
hl_color = blue
# right window text color
r_win_color = green
# default quality
quality = best
```


<a id="org6d89dec"></a>

## Followed List Import

Reflex-Curses can also mass import a list of channel names.

Place entries (one per line) in ```~/.config/reflex-curses/followed```

Reflex-Curses will resolve the Channel IDs on startup.
