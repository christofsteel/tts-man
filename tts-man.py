import os
import json
import shutil
import sys
import glob
import requests
import tempfile
import os.path
import argparse
import platform
import zipfile


modpath = os.path.join("Tabletop Simulator", "Mods")

if platform.system() == "Linux":
    localshare = os.path.join(os.environ["HOME"], ".local/share")
else:
    localshare = os.path.join(os.path.expanduser("~"), os.path.join("Document", "My Games"))
basepath = os.path.join(localshare, modpath)

workshoppath = os.path.join(basepath, "Workshop")
imagepath = os.path.join(basepath, "Images")
assetbundlespath = os.path.join(basepath, "Assetbundles")
modelpath = os.path.join(basepath, "Models")
WFI = os.path.join(workshoppath, "WorkshopFileInfos.json")


class Game:
    def __init__(self, name, directory, updatetime):
        self.name = name
        self.directory = directory
        self.id = int(os.path.splitext(os.path.basename(directory))[0])
        self.updatetime = updatetime
        with open(directory, 'r') as game_file:
            self._json = json.load(game_file)

        self.images = []
        self.models = []
        self.assetbundles = []
        self.types = []
        if 'TableURL' in self._json:
            self.images.append(self._json["TableURL"])
        if 'SkyURL' in self._json:
            self.images.append(self._json["SkyURL"])
        for obj in self._json["ObjectStates"]:
            self._addObj(obj)
        self.images = list(set(self.images))
        self.models = list(set(self.models))
        self.assetbundles = list(set(self.assetbundles))

    def _addObj(self, obj):
        if type(obj) == dict:
            for key, value in obj.items():
                if type(key) == str and key.endswith("URL") and value:
                    if value.endswith("{Unique}"):  #Weird bug...
                        value = value[:-8]
                    if key in ["FaceURL", "BackURL", "ImageURL", "DiffuseURL", "ImageSecondaryURL", "NormalURL", "URL"]:
                        self.images.append(value)
                    elif key in ["MeshURL", "ColliderURL"]:
                        self.models.append(value)
                    elif key in ["AssetbundleURL"]:
                        self.assetbundles.append(value)
                    elif key in ["PageURL"]:
                        pass
                    else:
                        print(f"[{self.name}] {key}: {value}")
                    self.types.append(key)
                elif type(value) == dict:
                    self._addObj(value)
                elif type(value) == list:
                    self._addObj(value)
        elif type(obj) == list:
            for it in obj:
                self._addObj(it)

    def writeFiles(self, fname):
        with open(fname, 'w') as f:
            for url in self.images:
                f.write(url + "\n")
            for url in self.models:
                f.write(url + "\n")

    def stripfilename(self, filename):
        return "".join(filter(lambda c: c.isalnum(), filename))

    def download_file(self, url, dl_filepath, ext=None):
        r = requests.get(url, stream=True)
        if r.status_code == 200:
            if ext is None:
                if r.headers["Content-Type"] == "image/jpeg":
                    ext = ".jpg"
                elif r.headers["Content-Type"] == "image/png":
                    ext = ".png"
                elif r.headers["Content-Type"] == "image/bmp":
                    ext = ".bmp"
                else:
                    print(f"WARNING: Could not guess extension for {r.headers['Content-Type']}")
                    if ".jpg" in url or ".jpeg" in url:
                        ext = ".jpg"
                    elif ".png" in url:
                        ext = ".png"
                    elif ".bmp" in url:
                        ext = ".bmp"
                    else:
                        raise RuntimeError

            print(f"Downloading {url} to {dl_filepath}{ext}")
            with tempfile.NamedTemporaryFile(delete=False) as f:
                name = f.name
                for chunk in r:
                    f.write(chunk)
            shutil.move(name, dl_filepath + ext)
            return 0
        else:
            print(f"fail: {url}") 
            return 1

    def download_files(self):
        missing = 0
        for f in self.images:
            dl_filepath = os.path.join(imagepath, self.stripfilename(f))        
            if not (os.path.exists(dl_filepath + ".jpg") \
                    or os.path.exists(dl_filepath + ".png")\
                    or os.path.exists(dl_filepath + ".bmp")):
                missing += self.download_file(f, dl_filepath)
        for f in self.models:
            dl_filepath = os.path.join(modelpath, self.stripfilename(f))        
            if not os.path.exists(dl_filepath + ".obj"):
                missing += self.download_file(f, dl_filepath, ".obj")
        for f in self.assetbundles:
            dl_filepath = os.path.join(assetbundlespath, self.stripfilename(f))        
            if not os.path.exists(dl_filepath + ".unity3d"):
                missing += self.download_file(f, dl_filepath, ".unity3d")
        print(f"Missing: {missing}")

    def bundle_files(self, filename):
        with zipfile.ZipFile(filename, 'w') as gamezip:
            for f in self.images:
                dl_filepaths = glob.glob(os.path.join(imagepath, self.stripfilename(f)) + ".*")
                for fp in dl_filepaths:
                    print(f"{fp} => {fp[len(localshare):]}")
                    gamezip.write(fp, fp[len(localshare):])
            for f in self.models:
                dl_filepaths = glob.glob(os.path.join(modelpath, self.stripfilename(f)) + ".obj")
                for fp in dl_filepaths:
                    print(f"{fp} => {fp[len(localshare):]}")
                    gamezip.write(fp, fp[len(localshare):])
            for f in self.assetbundles:
                dl_filepaths = glob.glob(os.path.join(assetbundlespath, self.stripfilename(f)) + ".unity3d")
                for fp in dl_filepaths:
                    print(f"{fp} => {fp[len(localshare):]}")
                    gamezip.write(fp, fp[len(localshare):])
            print(f"{os.path.normpath(self.directory)} => {os.path.normpath(self.directory)[len(localshare):]}")
            gamezip.write(os.path.normpath(self.directory), os.path.normpath(self.directory)[len(localshare):])
            gamezip.writestr(f"/tts-man-{self.id}.json", json.dumps({"Directory": self.directory, "Name": self.name, "UpdateTime": self.updatetime}))

class Workshop:
    def __init__(self):
        with open(WFI, 'r') as wfi_file:
            self._game_list = json.load(wfi_file)
        self.warnings = [e for e in self._game_list if not e['Directory'].endswith("json")]
        for game in self.warnings:
            print(f"Warning: could not parse {game['Name']}; not a JSON file")
        self._game_list = [e for e in self._game_list if e['Directory'].endswith("json")]

        self.game_list = [Game(g["Name"], g["Directory"], g["UpdateTime"]) for g in self._game_list]


    def print_games(self):
        for entry in self._game_list:
            print(entry["Name"])

    def find_game(self, prefix):
        return [game for game in self.game_list if game.name.startswith(prefix)]

    def install(self, zipf):
        with zipfile.ZipFile(zipf, 'r') as gamezip:
            p = zipfile.Path(zipf,"Tabletop Simulator/Mods/Workshop/")
            for f in p.iterdir():
                print(f)


def main():

    parser = argparse.ArgumentParser()
    cmdparser = parser.add_subparsers(dest="cmd")
    cmdparser.add_parser("list")
    dlparser = cmdparser.add_parser("download")
    dlparser.add_argument("game")
    bundleparser = cmdparser.add_parser("bundle")
    bundleparser.add_argument("game")
    bundleparser.add_argument("file")
    installparser = cmdparser.add_parser("install")
    installparser.add_argument("zip")
    args = parser.parse_args()

    workshop = Workshop()
    if args.cmd == "list":
        workshop.print_games()
    elif args.cmd == "download" or args.cmd == "bundle":
        games = workshop.find_game(args.game)
        if len(games) == 0:
            print(f"Could not find a game starting with {args.game}")
        if len(games) == 1:
            games[0].download_files()
            if args.cmd == "bundle":
                games[0].bundle_files(args.file)
        if len(games) > 1:
            print("Ambiguous game name. Found:")
            for game in games:
                print(f"\t{game.name}")
    elif args.cmd == "install":
        workshop.install(args.zip)


if __name__ == "__main__":
    main()
