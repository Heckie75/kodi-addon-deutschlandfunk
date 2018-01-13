#!/usr/bin/python
# -*- coding: utf-8 -*-

import json
import os
import re
import urlparse
import urllib2
import sys

import xbmc
import xbmcgui
import xbmcplugin
import xbmcaddon
import xmltodict

from lxml import html

__PLUGIN_ID__ = "plugin.audio.deutschlandfunk"

URL_STREAM_DLF = 'http://st01.dlf.de/dlf/01/128/mp3/stream.mp3'
URL_STREAM_DLK = 'http://st02.dlf.de/dlf/02/128/mp3/stream.mp3'
URL_STREAM_NOVA = 'http://st03.dlf.de/dlf/03/128/mp3/stream.mp3'
                           
URL_PODCASTS_DLF = 'http://www.deutschlandfunk.de/podcasts.2516.de.html?drpp%3Ahash=displayAllBroadcasts'
URL_PODCASTS_DLK = 'http://www.deutschlandfunkkultur.de/podcasts.2502.de.html?drpp%3Ahash=displayAllBroadcasts'
URL_PODCASTS_NOVA = 'https://www.deutschlandfunknova.de/podcasts'

settings = xbmcaddon.Addon(id=__PLUGIN_ID__);
addon_dir = xbmc.translatePath( settings.getAddonInfo('path') )

class Mediathek:

    _menu = None
    _addon_handle = None

    def __init__(self):
     
        self._menu = [
            { # root
                "path" : "",
                "node" : [
                    {
                        "path" : "dlf",
                        "name" : "Deutschlandfunk",
                        "icon" : "icon_dlf",
                        "node" : [
                            {
                                "path" : "stream",
                                "name" : "Deutschlandfunk",
                                "icon" : "icon_dlf",
                                "params" : [
                                    {
                                        "call" : "play",
                                        "url" : URL_STREAM_DLF
                                    }
                                ]
                            },
                            {
                                "path" : "podcasts",
                                "name" : "Podcasts",
                                "icon" : "icon_dlf_rss",
                                "params" : [
                                    {
                                        "call" : "parseDLF",
                                        "url" : URL_PODCASTS_DLF
                                    }
                                ],
                                "node" : []
                            }
                        ]
                    },
                    {
                        "path" : "dkultur",
                        "name" : "Deutschlandfunk Kultur",
                        "icon" : "icon_drk",
                        "node" : [
                            {
                                "path" : "stream",
                                "name" : "Deutschlandfunk Kultur",
                                "icon" : "icon_drk",
                                "params" : [
                                    {
                                        "call" : "play",             
                                        "url" : URL_STREAM_DLK
                                    }
                                ]
                            },
                            {
                                "path" : "podcasts",
                                "name" : "Podcasts",
                                "icon" : "icon_drk_rss",
                                "params" : [
                                    {
                                        "call" : "parseDLF",              
                                        "url" : URL_PODCASTS_DLK
                                    }
                                ],  
                                "node" : []
                            }
                        ]
                    },
                    {
                        "path" : "nova",
                        "name" : "Deutschlandfunk Nova",
                        "icon" : "icon_nova",
                        "node" : [
                            {
                                "path" : "stream",
                                "name" : "Deutschlandfunk Nova",
                                "icon" : "icon_nova",
                                "params" : [
                                    {
                                        "call" : "play",
                                        "url" : URL_STREAM_NOVA
                                    }
                                ]
                            },
                            {
                                "path" : "podcasts",
                                "name" : "Podcasts",
                                "icon" : "icon_nova_rss",
                                "params" : [
                                    {
                                        "call" : "parseNova",
                                        "url" : URL_PODCASTS_NOVA
                                    }
                                ],                        
                                "node" : []
                            }
                        ]
                    }
                ]
            }
        ]


    def _loadRss(self, url):

        _file = urllib2.urlopen(url)
        _data = _file.read()
        _file.close()

        return xmltodict.parse(_data)

        
        

    def playRss(self, parent, path, params):
    
        url = params["url"][0]
        rss_feed = self._loadRss(url)

        channel = rss_feed["rss"]["channel"]
        image = channel["image"]["url"]
        items = channel["item"]

        index = int(params["index"][0])
        
        item = items[index]
        if "enclosure" in item:
            stream_url = item["enclosure"]["@url"]
        else:
            stream_url = ["guid"]
        
        xbmc.executebuiltin('PlayMedia(%s)' % stream_url)
        
        
        
        
    def renderRss(self, parent, path, params):
        
        url = params["url"][0]
        rss_feed = self._loadRss(url)
                
        channel = rss_feed["rss"]["channel"]
        image = channel["image"]["url"]
        items = channel["item"]
        
        index = 0
        
        for item in items:
            
            entry = {
                    "path" : str(index),
                    "name" : item["title"],
                    "name2" : item["description"],
                    "icon" : image,
                    "params" : [
                        {
                            "call" : "playRss",
						    "index" : str(index),
                            "url" : url
                        }
                    ]
                }
                
            self._add_list_item(entry, path)

            index += 1

        xbmcplugin.endOfDirectory(self._addon_handle)


        
        
    def parseNova(self, parent, path, params):

        BASE_URL = "https://www.deutschlandfunknova.de/podcast/"
    
        url = params["url"][0]

        # download html site with podcast overview
        _file = urllib2.urlopen(url)
        _data = _file.read()
        _file.close()
        
        # parse site and read podcast meta data kindly provided as js
        _dom = html.fromstring(_data)
        _casts = _dom.xpath('//li[@class="item"]')    
        
        for c in _casts:

            _href = c.find("a").get("href")
            _path = _href.replace("/podcasts/download/", "")
            _img = c.find(".//img")
            
            xbmc.log(BASE_URL + _href.replace("/download", ""), xbmc.LOGNOTICE)
            
            entry = {
                    "path" : _path,
                    "name" : _img.get("alt"),
                    "icon" : _img.get("src"),
                    "params" : [
                        {
                            "call" : "renderRss",
                            "url" : BASE_URL + _path
                        }
                    ],
                    "node" : []
                }
            self._add_list_item(entry, path)

        xbmcplugin.endOfDirectory(self._addon_handle)
    
    
    
    

    def parseDLF(self, parent, path, params):
        
        url = params["url"][0]

        # download html site with podcast overview
        _file = urllib2.urlopen(url)
        _data = _file.read()
        _file.close()

        # parse site and read podcast meta data kindly provided as js
        _dom = html.fromstring(_data)
        _js_cast_defs = _dom.xpath('.//li/script[@type="text/javascript"]')    
        _regex = re.compile("window.podcastData_[0-9a-f_]+ = ")
        _regex2 = re.compile("};")

        podcasts = []
        for _def in _js_cast_defs:
            
            _def = _regex.sub("", _def.text)
            _def = _regex2.sub("}", _def)
            _json_def = json.loads(_def)
            podcasts += [ _json_def ]


        for podcast in podcasts:
            
            entry = {
                    "path" : podcast["id"],
                    "name" : podcast["title"],
                    "icon" : podcast["cover"],
                    "params" : [
                        {
                            "call" : "renderRss",
                            "url" : podcast["feeds"][0]["url"]
                        }
                    ],
                    "node" : []
                }
            self._add_list_item(entry, path)

        xbmcplugin.endOfDirectory(self._addon_handle)


    
    def play(self, parent, path, params):
        
        url = params["url"][0]
        xbmc.executebuiltin('PlayMedia(%s)' % url)




    def _get_node_by_path(self, path):
    
        if path == "/":
            return self._menu[0]
    
        tokens = path.split("/")[1:]
        directory = self._menu[0]
    
        while len(tokens) > 0:
            path = tokens.pop(0)
            for node in directory["node"]:
                if node["path"] == path:
                    directory = node
                    break
    
        return directory




    def _build_param_string(self, params, current = ""):
    
        if params == None:
            return current
    
        for obj in params:
            for name in obj:
                current += "?" if len(current) == 0 else "&"
                current += name + "=" + str(obj[name])
                
        return current




    def _add_list_item(self, entry, path):
    
        if path == "/":
            path = ""
    
        item_path = path + "/" + entry["path"]
        item_id = item_path.replace("/", "_")
    
        param_string = ""
        if "params" in entry:
            param_string = self._build_param_string(entry["params"],
                current = param_string)
    
        if "node" in entry:
            is_folder = True
        else:
            is_folder = False
    
        label = entry["name"]
        
        if settings.getSetting("label%s" % item_id) != "":
            label = settings.getSetting("label%s" % item_id)
    
        if "icon" in entry and entry["icon"].startswith("http"):
            icon_file = entry["icon"]
    
        elif "icon" in entry:
            icon_file = os.path.join(addon_dir, 
                                     "resources", 
                                     "assets", 
                                     entry["icon"] + ".png")
        else:
            icon_file = None
    
        li = xbmcgui.ListItem(label, iconImage = icon_file)

        if "name2" in entry:
            li.setLabel2(entry["name2"])
        
        xbmcplugin.addDirectoryItem(handle=self._addon_handle,
                                listitem=li,
                                url="plugin://" + __PLUGIN_ID__
                                + item_path
                                + param_string,
                                isFolder=is_folder)




    def _browse(self, parent, path):
        
        for entry in parent["node"]:
            self._add_list_item(entry, path)
    
        xbmcplugin.endOfDirectory(self._addon_handle)




    def handle(self, argv):
        
        self._addon_handle = int(argv[1])
        
        path = urlparse.urlparse(argv[0]).path
        url_params = urlparse.parse_qs(argv[2][1:])

        node = self._get_node_by_path(path)
        if "call" in url_params:
        
            getattr(self, url_params["call"][0])(parent = node, 
                                        path = path, 
                                        params = url_params)

        else:
            self._browse(parent = node, path = path)



if __name__ == '__main__':

    mediathek = Mediathek()
    mediathek.handle(sys.argv)
    
