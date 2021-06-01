from resources.lib.rssaddon.abstract_rss_addon import AbstractRssAddon
from resources.lib.rssaddon.http_status_error import HttpStatusError
from resources.lib.rssaddon.http_client import http_request

from bs4 import BeautifulSoup
import json
import os

import xbmc
import xbmcgui
import xbmcplugin
import xbmcaddon


class DeutschlandfunkAddon(AbstractRssAddon):

    __PLUGIN_ID__ = "plugin.audio.deutschlandfunk"

    URL_STREAMS_RPC = "https://srv.deutschlandradio.de/config-feed.2828.de.rpc"

    URL_PODCASTS_DLF = "https://www.deutschlandfunk.de/podcasts.2516.de.html?drpp%3Ahash=displayAllBroadcasts"
    URL_PODCASTS_DLK = "https://www.deutschlandfunkkultur.de/podcasts.2502.de.html?drpp%3Ahash=displayAllBroadcasts"
    URL_PODCASTS_NOVA = "https://www.deutschlandfunknova.de/podcasts"

    addon = xbmcaddon.Addon(id=__PLUGIN_ID__)

    def __init__(self, addon_handle):

        super().__init__(self.__PLUGIN_ID__, addon_handle)

    def _make_root_menu(self):

        nodes = [
            {
                "path": "dlf",
                "name": "Deutschlandfunk",
                "icon": os.path.join(
                    self.addon_dir, "resources", "assets", "icon_dlf.png"),
                "node": []
            },
            {
                "path": "dkultur",
                "name": "Deutschlandfunk Kultur",
                "icon": os.path.join(
                    self.addon_dir, "resources", "assets", "icon_drk.png"),
                "node": []
            },
            {
                "path": "nova",
                "name": "Deutschlandfunk Nova",
                "icon": os.path.join(
                    self.addon_dir, "resources", "assets", "icon_nova.png"),
                "node": []
            }
        ]

        for entry in nodes:
            self.add_list_item(entry, "/")

        xbmcplugin.endOfDirectory(self.addon_handle, updateListing=False)

    def _make_station_menu(self, path):

        try:
            _json, _cookies = http_request(self.addon, self.URL_STREAMS_RPC)
            meta = json.loads(_json)

        except HttpStatusError as error:
            xbmc.log("HTTP Status Error: %s, path=%s" %
                     (error.message, path), xbmc.LOGERROR)
            xbmcgui.Dialog().notification(self.addon.getLocalizedString(32151), error.message)
            return

        nodes = list()
        if "/dlf" == path:
            nodes.append({
                "path": "stream",
                "name": "Deutschlandfunk",
                "icon": os.path.join(
                        self.addon_dir, "resources", "assets", "icon_dlf.png"),
                "stream_url": meta['livestreams']['dlf']['mp3']['high'],
                "type": "music",
                "specialsort": "top"
            })
            nodes.append({
                "path": "podcasts",
                "name": "Podcasts",
                "icon": os.path.join(
                        self.addon_dir, "resources", "assets", "icon_dlf_rss.png"),
                "node": []
            })

        elif "/dkultur" == path:
            nodes.append({
                "path": "stream",
                "name": "Deutschlandfunk Kultur",
                "icon": os.path.join(
                        self.addon_dir, "resources", "assets", "icon_drk.png"),
                "stream_url": meta['livestreams']['dlf_kultur']['mp3']['high'],
                "type": "music",
                "specialsort": "top"
            })
            nodes.append({
                "path": "podcasts",
                "name": "Podcasts",
                "icon": os.path.join(
                        self.addon_dir, "resources", "assets", "icon_drk_rss.png"),
                "node": []
            })

        elif "/nova" == path:
            nodes.append({
                "path": "stream",
                "name": "Deutschlandfunk Nova",
                "icon": os.path.join(
                        self.addon_dir, "resources", "assets", "icon_nova.png"),
                "stream_url": meta['livestreams']['dlf_nova']['mp3']['high'],
                "type": "music",
                "specialsort": "top"
            })
            nodes.append({
                "path": "podcasts",
                "name": "Podcasts",
                "icon": os.path.join(
                        self.addon_dir, "resources", "assets", "icon_nova_rss.png"),
                "node": []
            })

        for entry in nodes:
            self.add_list_item(entry, path)

        xbmcplugin.endOfDirectory(self.addon_handle, updateListing=False)

    def _parse_nova(self, path):

        _BASE_URL = "https://www.deutschlandfunknova.de/podcast/"

        # download html site with podcast overview
        _data, _cookies = http_request(self.addon, self.URL_PODCASTS_NOVA)

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
            self.add_list_item(entry, path)

        xbmcplugin.addSortMethod(
            self.addon_handle, xbmcplugin.SORT_METHOD_LABEL)

        xbmcplugin.endOfDirectory(self.addon_handle, updateListing=False)

    def _parse_dlf(self, path, url):

        # download html site with podcast overview
        _data, _cookies = http_request(self.addon, url)

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
            self.add_list_item(entry, path)

        xbmcplugin.addSortMethod(
            self.addon_handle, xbmcplugin.SORT_METHOD_LABEL)

        xbmcplugin.endOfDirectory(self.addon_handle, updateListing=False)

    def route(self, path, url_params):

        splitted_path = path.split("/")
        if len(splitted_path) == 3 and splitted_path[2] == "podcasts":

            if splitted_path[1] == "dlf":
                self._parse_dlf(path, self.URL_PODCASTS_DLF)

            elif splitted_path[1] == "dkultur":
                self._parse_dlf(path, self.URL_PODCASTS_DLK)

            elif splitted_path[1] == "nova":
                self._parse_nova(path)

        elif len(splitted_path) == 2 and splitted_path[1] != "":
            self._make_station_menu(path)

        else:
            self._make_root_menu()
