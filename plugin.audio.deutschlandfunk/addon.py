from bs4 import BeautifulSoup
from datetime import datetime
import base64
import json
import os
import re
import requests
import sys
import urllib.parse
import xmltodict

import xbmc
import xbmcgui
import xbmcplugin
import xbmcaddon
import xbmcvfs

__PLUGIN_ID__ = "plugin.audio.deutschlandfunk"

URL_STREAMS_RPC = "https://srv.deutschlandradio.de/config-feed.2828.de.rpc"

URL_PODCASTS_DLF = "https://www.deutschlandfunk.de/podcasts.2516.de.html?drpp%3Ahash=displayAllBroadcasts"
URL_PODCASTS_DLK = "https://www.deutschlandfunkkultur.de/podcasts.2502.de.html?drpp%3Ahash=displayAllBroadcasts"
URL_PODCASTS_NOVA = "https://www.deutschlandfunknova.de/podcasts"

# see https://forum.kodi.tv/showthread.php?tid=112916
_MONTHS = ["Jan", "Feb", "Mar", "Apr", "May",
           "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

settings = xbmcaddon.Addon(id=__PLUGIN_ID__)
addon_dir = xbmcvfs.translatePath(settings.getAddonInfo('path'))


class HttpStatusError(Exception):

    message = ""

    def __init__(self, msg):

        self.message = msg


class Mediathek:

    _menu = None

    addon_handle = None

    def __init__(self):

        try:
            meta = self._load_json(URL_STREAMS_RPC)
        except HttpStatusError as error:
            xbmc.log("HTTP Status Error: %s, path=%s" %
                     (error.message, URL_STREAMS_RPC), xbmc.LOGERROR)
            xbmcgui.Dialog().notification("HTTP Status Error", error.message)
            return

        self._menu = [
            {  # root
                "path": "",
                "node": [
                    {
                        "path": "dlf",
                        "name": "Deutschlandfunk",
                        "icon": os.path.join(
                            addon_dir, "resources", "assets", "icon_dlf.png"),
                        "node": [
                            {
                                "path": "stream",
                                "name": "Deutschlandfunk",
                                "icon": os.path.join(
                                    addon_dir, "resources", "assets", "icon_dlf.png"),
                                "stream_url": meta['livestreams']['dlf']['mp3']['high'],
                                "type": "music",
                                "specialsort": "top"
                            },
                            {
                                "path": "podcasts",
                                "name": "Podcasts",
                                "icon": os.path.join(
                                    addon_dir, "resources", "assets", "icon_dlf_rss.png"),
                                "node": []
                            }
                        ]
                    },
                    {
                        "path": "dkultur",
                        "name": "Deutschlandfunk Kultur",
                        "icon": os.path.join(
                            addon_dir, "resources", "assets", "icon_drk.png"),
                        "node": [
                            {
                                "path": "stream",
                                "name": "Deutschlandfunk Kultur",
                                "icon": os.path.join(
                                    addon_dir, "resources", "assets", "icon_drk.png"),
                                "stream_url": meta['livestreams']['dlf_kultur']['mp3']['high'],
                                "type": "music",
                                "specialsort": "top"
                            },
                            {
                                "path": "podcasts",
                                "name": "Podcasts",
                                "icon": os.path.join(
                                    addon_dir, "resources", "assets", "icon_drk_rss.png"),
                                "node": []
                            }
                        ]
                    },
                    {
                        "path": "nova",
                        "name": "Deutschlandfunk Nova",
                        "icon": os.path.join(
                            addon_dir, "resources", "assets", "icon_nova.png"),
                        "node": [
                            {
                                "path": "stream",
                                "name": "Deutschlandfunk Nova",
                                "icon": os.path.join(
                                    addon_dir, "resources", "assets", "icon_nova.png"),
                                "stream_url": meta['livestreams']['dlf_nova']['mp3']['high'],
                                "type": "music",
                                "specialsort": "top"
                            },
                            {
                                "path": "podcasts",
                                "name": "Podcasts",
                                "icon": os.path.join(
                                    addon_dir, "resources", "assets", "icon_nova_rss.png"),
                                "node": []
                            }
                        ]
                    }
                ]
            }
        ]

    def _parse_nova(self, path):

        _BASE_URL = "https://www.deutschlandfunknova.de/podcast/"

        # download html site with podcast overview
        _data = self._request_get(URL_PODCASTS_NOVA)

        # parse site and read podcast meta data kindly provided as js
        soup = BeautifulSoup(_data, 'html.parser')
        _casts = soup.select('li.item')

        for _cast in _casts:

            _href = _cast.a.get("href")
            _path = _href.replace("/podcasts/download/", "")
            _img = _cast.img

            entry = {
                "path": _path,
                "name": _img.get("alt"),
                "icon": _img.get("src"),
                "params": [
                    {
                        "rss": _BASE_URL + _path
                    }
                ],
                "node": []
            }
            self._add_list_item(entry, path)

        xbmcplugin.endOfDirectory(self.addon_handle)

    def _parse_dlf(self, path, url):

        # download html site with podcast overview
        _data = self._request_get(url)

        soup = BeautifulSoup(_data, 'html.parser')
        _js_cast_defs = soup.select('span.abo.dradio-podlove')

        for _def in _js_cast_defs:
            entry = {
                "path": _def["data-buttonid"],
                "name": _def["data-title"],
                "icon": _def["data-logosrc"],
                "params": [
                    {
                        "rss": _def["data-url"]
                    }
                ],
                "node": []
            }
            self._add_list_item(entry, path)

        xbmcplugin.endOfDirectory(self.addon_handle)

    def _request_get(self, url):

        useragent = f"{settings.getAddonInfo('id')}/{settings.getAddonInfo('version')} (Kodi/{xbmc.getInfoLabel('System.BuildVersionShort')})"
        headers = {'User-Agent': useragent}
        res = requests.get(url, headers=headers)

        if res.status_code == 200:
            return res.text

        else:
            raise HttpStatusError(
                "Unexpected HTTP Status %i for %s" % (res.status_code, url))

    def _load_json(self, url):

        return json.loads(self._request_get(url))

    def _load_rss(self, url):

        def _parse_item(_ci):

            if "enclosure" in _ci and "@url" in _ci["enclosure"]:
                stream_url = _ci["enclosure"]["@url"]
                if _ci["enclosure"]["@type"].split("/")[0] == "video":
                    _type = "video"
                else:
                    _type = "music"
            elif "guid" in _ci and _ci["guid"]:
                # not supported yet
                return None
            else:
                return None

            if "itunes:image" in _ci and "@href" in _ci["itunes:image"]:
                item_image = _ci["itunes:image"]["@href"]
            else:
                item_image = image

            if "pubDate" in _ci:
                _f = re.findall(
                    "(\d{1,2}) (\w{3}) (\d{4}) (\d{2}):(\d{2}):(\d{2})", _ci["pubDate"])

                if _f:
                    _m = _MONTHS.index(_f[0][1]) + 1
                    pubDate = datetime(year=int(_f[0][2]), month=_m, day=int(_f[0][0]), hour=int(
                        _f[0][3]), minute=int(_f[0][4]), second=int(_f[0][5]))

                else:
                    pubDate = None

            return {
                "name": _ci["title"],
                "name2": _ci["description"] if "description" in _ci else "",
                "date": pubDate,
                "icon": item_image,
                "stream_url": stream_url,
                "type": _type
            }

        res = self._request_get(url)
        if res.startswith("<?xml"):
            rss_feed = xmltodict.parse(res)

        else:
            raise HttpStatusError("Unexpected content for podcast %s" % url)

        channel = rss_feed["rss"]["channel"]
        title = channel["title"] if "title" in channel else ""
        description = channel["description"] if "description" in channel else ""

        if "image" in channel and "url" in channel["image"]:
            image = channel["image"]["url"]
        elif "itunes:image" in channel:
            image = channel["itunes:image"]["@href"]
        else:
            image = None

        items = []
        if type(channel["item"]) is list:
            for _ci in channel["item"]:
                item = _parse_item(_ci)
                if item is not None:
                    items += [item]

        else:
            item = _parse_item(channel["item"])
            if item is not None:
                items += [item]

        return title, description, image, items

    def _render_rss(self, path, url):

        try:
            title, description, image, items = self._load_rss(url)

        except HttpStatusError as error:
            xbmc.log("HTTP Status Error: %s, path=%s" %
                     (error.message, path), xbmc.LOGERROR)
            xbmcgui.Dialog().notification("HTTP Status Error", error.message)

        else:
            if len(items) > 0:

                entry = {
                    "path": "latest",
                    "name": title,
                    "name2": description,
                    "icon": image,
                    "date": datetime.now(),
                    "specialsort": "top",
                    "type": items[0]["type"],
                    "params": [
                        {
                            "play_latest": url
                        }
                    ]
                }
                self._add_list_item(entry, path, playable=True)

            for item in items:
                li = self._create_list_item(item)
                xbmcplugin.addDirectoryItem(handle=self.addon_handle,
                                            listitem=li,
                                            url=item["stream_url"],
                                            isFolder=False)

            if "setDateTime" in dir(li):  # available since Kodi v20
                xbmcplugin.addSortMethod(
                    self.addon_handle, xbmcplugin.SORT_METHOD_DATE)
            xbmcplugin.endOfDirectory(self.addon_handle)

    def _create_list_item(self, item):

        li = xbmcgui.ListItem(label=item["name"])

        if "name2" in item:
            li.setProperty("label2", item["name2"])

        if "stream_url" in item:
            li.setPath(item["stream_url"])

        if "type" in item:
            li.setInfo(item["type"], {"Title": item["name"]})

        if "icon" in item and item["icon"]:
            li.setArt({"icon": item["icon"]})
        else:
            li.setArt({"icon": os.path.join(
                addon_dir, "resources", "assets", "icon.png")}
            )

        if "date" in item and item["date"]:
            if "setDateTime" in dir(li):  # available since Kodi v20
                li.setDateTime(item["date"].strftime("%Y-%m-%dT%H:%M:%SZ"))
            else:
                pass

        if "specialsort" in item:
            li.setProperty("SpecialSort", item["specialsort"])

        return li

    def _add_list_item(self, entry, path, playable=False):

        def _build_param_string(params, current=""):

            if params == None:
                return current

            for obj in params:
                for name in obj:
                    enc_value = base64.urlsafe_b64encode(
                        obj[name].encode("utf-8"))
                    current += "?" if len(current) == 0 else "&"
                    current += name + "=" + str(enc_value, "utf-8")

            return current

        if path == "/":
            path = ""

        item_path = path + "/" + entry["path"]

        param_string = ""
        if "params" in entry:
            param_string = _build_param_string(entry["params"],
                                               current=param_string)

        li = self._create_list_item(entry)

        is_folder = "node" in entry
        if not is_folder and "stream_url" in entry:
            url = entry["stream_url"]
            playable = True
        else:
            url = "".join(
                ["plugin://", __PLUGIN_ID__, item_path, param_string])

        if playable:
            li.setProperty("IsPlayable", "true")

        xbmcplugin.addDirectoryItem(handle=self.addon_handle,
                                    listitem=li,
                                    url=url,
                                    isFolder=is_folder)

    def _play_latest(self, url):

        try:
            title, description, image, items = self._load_rss(url)
            item = items[0]
            li = self._create_list_item(item)
            xbmcplugin.setResolvedUrl(self.addon_handle, True, li)

        except HttpStatusError as error:

            xbmcgui.Dialog().notification("HTTP Status Error", error.message)

    def _browse(self, path):

        def _get_node_by_path(path):

            if path == "/":
                return self._menu[0]

            tokens = path.split("/")[1:]
            node = self._menu[0]

            while len(tokens) > 0:
                path = tokens.pop(0)
                for n in node["node"]:
                    if n["path"] == path:
                        node = n
                        break

            return node

        node = _get_node_by_path(path)
        for entry in node["node"]:
            self._add_list_item(entry, path)

        xbmcplugin.endOfDirectory(self.addon_handle)

    def handle(self, argv):

        def decode_param(encoded_param):

            return base64.urlsafe_b64decode(encoded_param).decode("utf-8")

        self.addon_handle = int(argv[1])

        path = urllib.parse.urlparse(argv[0]).path.replace("//", "/")
        splitted_path = path.split("/")
        url_params = urllib.parse.parse_qs(argv[2][1:])

        if "rss" in url_params:
            url = decode_param(url_params["rss"][0])
            self._render_rss(path, url)
        elif "play_latest" in url_params:
            url = decode_param(url_params["play_latest"][0])
            self._play_latest(url)
        elif len(splitted_path) == 3 and splitted_path[2] == "podcasts":
            if splitted_path[1] == "dlf":
                self._parse_dlf(path, URL_PODCASTS_DLF)
            elif splitted_path[1] == "dkultur":
                self._parse_dlf(path, URL_PODCASTS_DLK)
            elif splitted_path[1] == "nova":
                self._parse_nova(path)
        else:
            self._browse(path=path)


if __name__ == '__main__':

    mediathek = Mediathek()
    mediathek.handle(sys.argv)
