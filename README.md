# TTS-Man

A simple Tabletop Simulator manager.

## Installation

This script needs the Python library: `requests`

## Usage

```
python tts-man.py list
```

Lists all available Mods

```
python tts-man.py download <Game>
```

Downloads all assets of the game called `<Game>`. You do not need to provide the full name, it can be a prefix of the name. If the prefix is not unique, tts-man will tell you.

```
python tts-man.py bundle <Game> <zipfile>
```

Bundles the game `<Game>` and stores it as `<zipfile>`

```
python tts-man.py install <zipfile>
```

This is a WIP and does not work at the moment. To install a zipfile you have to manually extract the file to `~/.local/Tabletop Simulator/Mods/Workshop` and update your `~/.local/Tabletop Simulator/Mods/Workshop/WorkshopFileInfos.json`. See the `tts-man-<gameid>.json` file, that is included in an exported game.

# License

Apache 2.0
