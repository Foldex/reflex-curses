#!/usr/bin/env bash
# Basic dmenu script to play currently online followed channels
TWITCH_URL="https://twitch.tv/$CHOICE"
CHOICE=$(twitch-curses -f | dmenu -p "Select Stream:")

if [[ -n "$CHOICE" ]]; then
	streamlink $TWITCH_URL
fi

