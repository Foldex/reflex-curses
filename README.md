# No longer maintained

Twitch has completed the shutdown for the version of the API that this used. 

As the newer API is much more limited in functionality, I'm no longer maintaining this project.

<p align="center">
  <img src="/reflex.png" title="reflex-curses"/>
</p>

- [Description](#desc)
- [Changes](#changes)
- [Dependencies](#depend)
  - [Python](#python_dep)
  - [External](#ext_dep)
  - [Optional](#opt_dep)
- [Install](#install)
  - [AUR](#install_aur)
  - [Setuptools](#install_st)
  - [Manual](#install_manual)
- [Usage](#usage)
- [Default Keybinds](#def_keys)
  - [Page Navigation](#page_keys)
  - [Swap Views](#view_keys)
  - [Search](#search_keys)
  - [Quality Select](#quality_keys)
  - [Follow List](#follow_keys)
  - [Misc List](#misc_keys)
- [Configuration](#config)
  - [Config File](#conf_file)
  - [IRC](#irc)
	- [Weechat](#weechat)
	- [Irssi](#irssi)
  - [Followed List Import](#follow_import)

<a id="desc"></a>

# Description

Reflex-Curses is a TUI/CLI wrapper around streamlink, allowing for easy launching
of twitch.tv streams from your terminal.

Fork of [twitch-curses](https://gitlab.com/corbie/twitch-curses) with added features.

<a id="changes"></a>

# Changes

- Rewritten with classes
- Launch multiple streams at once
- Stream process no longer tied to terminal (setsid)
- Launch chat for selected stream (browser/weechat/irssi)
- Copy channel URL to clipboard (xclip)
- Locally follow channels (No account needed) (+Imports from file/twitch user)
- Custom Config File
- VOD Support
- Search by game name
- Top streams view
- Language filter (Game search only)
- Vim like keybinds
- Updated to Twitch v5 API
- Color support
- Fixed crashing with super small terminal resizing
- Run one off cli commands

<a id="depend"></a>

# Dependencies

<a id="python_dep"></a>

## Python

- Python 3.6
- python-requests

<a id="ext_dep"></a>

## External

- streamlink (launching streams)
- xclip (clipboard support)
- setsid (detach player from terminal)

<a id="opt_dep"></a>

## Optional

- firefox (default browser)
- mpv (default player)
- urxvt (default terminal)
- weechat / irssi (irc)

<a id="install"></a>

# Installation

<a id="install_aur"></a>

## Arch AUR

`yay -S reflex-curses`

<a id="install_st"></a>

## Setuptools

System: `python setup.py install`

User: `python setup.py install --user`

<a id="install_manual"></a>

## Manual

`sudo make install`

<a id="usage"></a>

# Usage

```
reflex-curses [OPTION]

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
              NOTE: Currently limited to the results_limit (default: 75), large lists might not fully import.

       -v     Print version
```

More info available from the man page: `man reflex-curses`

An example dmenu script is [Here](./scripts/dmenu_streams.sh)

<a id="def_keys"></a>

# Default Keybinds

<a id="page_keys"></a>

## Page Navigation

| Key       | Description                               |
|---------  |-----------------------------------------  |
| h         | Go back                                   |
| j         | Move cursor down                          |
| k         | Move cursor up                            |
| l / Enter | Enter menu or launch stream               |
| n         | Next Page                                 |
| p         | Previous page                             |
| r         | Refresh last query                        |

<a id="view_keys"></a>

## Swap Views

| Key       | Description                               |
|---------  |-----------------------------------------  |
| f         | Go to followed view                       |
| s         | Go to top streams view                    |
| t         | Go to top games view                      |
| v         | Go to VOD view                            |

<a id="search_keys"></a>

## Search

| Key       | Description                               |
|---------  |-----------------------------------------  |
| /         | General Search                            |
| g         | Search by Game Name (exact)               |

<a id="quality_keys"></a>

## Quality Selection

| Key       | Description                               |
|---------  |-----------------------------------------  |
| -         | Decrease quality                          |
| =         | Increase quality                          |

<a id="follow_keys"></a>

## Follow List

| Key       | Description                                |
|---------  |------------------------------------------  |
| a         | Add channel to followed list               |
| d         | Delete channel from followed list          |
| i         | Import follows from twitch user (limited)  |
| o         | Toggle online/all streams in followed list |

<a id="misc_keys"></a>

## Misc

| Key       | Description                               |
|---------  |-----------------------------------------  |
| c         | Open chat with chat method                |
| y         | Yank channel url                          |
| q         | Quit                                      |

<a id="config"></a>

# Configuration

Configuration files are stored in `~/.config/reflex-curses`

<a id="conf_file"></a>

## Config File

Config file is stored in `~/.config/reflex-curses/config`

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
t_stream = s
t_game = t
search = /
vods = v
yank = y
page+ = n
page- = p
qual+ = =
qual- = -

[exec]
browser = firefox --new-window
chat_method = browser
player = mpv --force-window=yes
streamlink = streamlink -t '{author} - {title}' --twitch-disable-hosting 
term = urxvt -e

[twitch]
client_id = caozjg12y6hjop39wx996mxn585yqyk
lang =
results_limit = 75
retry_limit = 3

[ui]
default_state = games
hl_color = blue
l_win_color = white
r_win_color = green
quality = best
show_borders = True
show_keys = True

[irc]
address = irc.chat.twitch.tv
network = reflex
no_account = True
port = 6697
```

<a id="irc"></a>

## IRC

Reflex will by default connect to the saved network `reflex`.

To connect to twitch irc, you must either connect with the nick
`justinfanRANDOMNUMBERHERE` or use an [OAUTH Token](https://twitchapps.com/tmi/)
for your account.

For more info, see the [Twitch IRC
Documentation](https://dev.twitch.tv/docs/irc/guide)

<a id="weechat"></a>

### Weechat

If you are connecting with weechat and using `no_account`, no configuration
should be necessary, as reflex can add the network itself through launch arguments.

If using an account, see the above section on getting your oauth token and add
it to your saved network.

NOTE: Reflex uses `irc.server.network_name.autojoin` in order to automatically
connect to a channel when launched. It will overwrite the variable should it
exist.

<a id="irssi"></a>

### Irssi

Irssi unfortunately does not appear to support running commands through launch
arguments, so support is much more limited in comparison. Only the `network`
option is supported at this time. Launching chat will also only copy the join
command to your clipboard instead of automatically joining the channel.

If using an account, see the above section on getting your oauth token and add
it to your saved network.

<a id="follow_import"></a>

## Followed List Import

In addition to the -i flag, reflex-curses can also mass import a list of channel names from a file.

Place entries (one per line) in `~/.config/reflex-curses/followed`

Reflex-Curses will resolve the Channel IDs on startup.
