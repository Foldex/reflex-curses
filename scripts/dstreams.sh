#!/usr/bin/env bash
# Basic dmenu script to play currently online followed channels
CHOICE=$(reflex-curses -f | dmenu -p "Select Stream:")
TWITCH_URL="https://twitch.tv/$CHOICE"

if [[ -n "$CHOICE" ]]; then
	streamlink $TWITCH_URL
fi

