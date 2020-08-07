import pixivpy3 as pixiv
import sys
import yaml
import os
import argparse
from urllib import parse as urlparse
import requests
import mimetypes

class PixivDL:
    def __init__(self, login=None, password=None, archive=None, nameformat="$title$"):
        self.api = pixiv.AppPixivAPI()
        if login and password:
            self.api.login(login, password)

        if archive:
            self.archive = set(archive)
        else:
            self.archive = set()

        self.nameformat = nameformat

    def get_following_ids(self, user_id):
        offset = 0
        while True:
            user_previews = self.api.user_following(user_id, offset=offset)["user_previews"]
            if not user_previews:
                break
            offset += len(user_previews)

            for preview in user_previews:
                yield int(preview["user"]["id"])
            

    def get_work_ids(self, user_id):
        offset = 0
        while True:
            illusts = self.api.user_illusts(user_id, offset=offset)["illusts"]
            if not illusts:
                break
            offset += len(illusts)

            for illust in illusts:
                yield int(illust["id"])

    def get_illust_details(self, illust_id):
        details = self.api.illust_detail(illust_id)["illust"]
        info = {
            "id": details["id"],
            "title": details["title"],
            "caption": details["caption"],
            "userid": details["user"]["id"],
            "username": details["user"]["name"],
            "account": details["user"]["account"]
        }

        urls = [x["image_urls"]["original"] for x in details["meta_pages"]]
        if "original_image_url" in details["meta_single_page"]:
            urls.append(details["meta_single_page"]["original_image_url"])
        
        return info, urls

    def download_illust(self, illust_id):
        if illust_id in self.archive:
            return None

        info, urls = self.get_illust_details(illust_id)

        name = self.nameformat
        for k, v in info.items():
            name = name.replace("$%s$" % k, str(v))


        folder = os.path.split(name)[0]
        
        if folder and not os.path.isdir(folder):
            os.makedirs(folder)

        for i, url in enumerate(urls):
            r = requests.get(url, headers={"referer": "https://www.pixiv.net/en/artworks/%d" % illust_id})

            ext = mimetypes.guess_extension(r.headers['content-type'])

            if len(urls) > 1:
                filename = "%s - %d%s" % (name, i+1, ext)
            else:
                filename = "%s%s" % (name, ext)

            with open(filename, "wb") as f:
                f.write(r.content)
        self.archive.add(illust_id)
        return info

    def save_archive(self, filename):
        with open(filename, "w") as f:
            f.write("\n".join([str(x) for x in self.archive]) + "\n")

    def load_archive(self, filename):
        with open(filename, "r") as f:
            self.archive = self.archive.union([int(x) for x in f.read().split("\n")[:-1]])


parser = argparse.ArgumentParser(prog="pixiv-dl")

operation_group = parser.add_mutually_exclusive_group(required=True)
operation_group.add_argument('-f', '--following', action='store_const', dest='op', const='following')
operation_group.add_argument('-w', '--works', action='store_const', dest='op', const='works')
operation_group.add_argument('-i', '--illusts', action='store_const', dest='op', const='download')

parser.add_argument('-a', '--archive')
parser.add_argument('-c', '--credentials')
parser.add_argument('-n', '--nameformat', default='$id$')

parser.add_argument('IDs', nargs='+', type=int)

args = parser.parse_args(sys.argv[1:])

login = None
password = None

if args.credentials:
    with open(args.credentials, "r") as f:
        c = f.read().split("\n")
        login = c[0]
        password = c[1]



p = PixivDL(login, password, nameformat=args.nameformat)

if args.archive:
    if os.path.isfile(args.archive):
        p.load_archive(args.archive)

if args.op == 'following':
    for user_id in args.IDs:
        for artist_id in p.get_following_ids(user_id):
            for illust_id in p.get_work_ids(artist_id):
                p.download_illust(illust_id)
                if args.archive: p.save_archive(args.archive)
                
elif args.op == 'works':
    for artist_id in args.IDs:
        for illust_id in p.get_work_ids(artist_id):
            p.download_illust(illust_id)
            if args.archive: p.save_archive(args.archive)

elif args.op == 'download':
    for illust_id in args.IDs:
        i = p.download_illust(illust_id)
        if i:
            print("Downloaded %s from %s with id %d." % (i["title"], i["username"], i["id"]))
        if args.archive: p.save_archive(args.archive)