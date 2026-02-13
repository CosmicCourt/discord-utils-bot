# Olfin Swimmer
A Discord bot designed to do a small handful of things, from a growing list.
The name does not mean anything, it was random nonsense that came to mind.

## Features
- Mass deletion of messages
- VoiceWork: Playback of audio files over a voice channel, reading from [/Assets/Music](https://github.com/CosmicCourt/discord-utils-bot/tree/main/Assets/Music) (supports subfolders) or a web link (eventually)
- Configurable time-based message deletion per-channel
- Automatic deletion of messages by rule-matching users in forum posts
- Logging of message editing and message deletion to external servers (would you believe I'm in a server with someone who deletes Dyno's logging messages? Yeah, I'm taking them somewhere else if you're gonna start that)

## Requirements
- `discord.py <= 2.6.4`

### VoiceWork
- `PyNaCl <= 1.6.2`
- `ffmpeg; installed locally, with the .exe on PATH if on Windows`
- `libopus (library placed in Assets/Libraries/libopus; libopus.so* for Linux, libopus.dll for Windows)`