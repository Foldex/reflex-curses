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

Default Config Example:

```
[keys]
add = a
chat = c
delete = d
followed = f
game = g
back = h
down = j
up = k
forward = l
online = o
quit = q
refresh = r
top = t
search = /
vods = v
yank = y
page+ = n
page- = p
qual+ = =
qual- = -

[exec]
browser = firefox
browser_flag = --new-window
chat_method = browser
player = mpv
term = urxvt
term_flag = -e

[twitch]
client_id = caozjg12y6hjop39wx996mxn585yqyk
lang =
query_limit = 75
retry_limit = 3

[ui]
hl_color = blue
r_win_color = green
quality = best

[irc]
address = irc.chat.twitch.tv
network = reflex
port = 6697
```


<a id="org6d89dec"></a>

## Followed List Import

Reflex-Curses can also mass import a list of channel names.

Place entries (one per line) in ```~/.config/reflex-curses/followed```

Reflex-Curses will resolve the Channel IDs on startup.
