# -*- coding: utf-8 -*-

import os
import sys
from urllib import parse

import requests
import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin
import xbmcvfs
from bs4 import BeautifulSoup
from requests import Session
from xbmcaddon import Addon

__addon__: Addon = xbmcaddon.Addon()
__author__: str = __addon__.getAddonInfo('author')
__scriptid__: str = __addon__.getAddonInfo('id')
__scriptname__: str = __addon__.getAddonInfo('name')
__version__: str = __addon__.getAddonInfo('version')

__cwd__: str = xbmcvfs.translatePath(__addon__.getAddonInfo('path'))
__profile__: str = xbmcvfs.translatePath(__addon__.getAddonInfo('profile'))
__temp__: str = xbmcvfs.translatePath(os.path.join(__profile__, 'temp'))

HANDLE = int(sys.argv[1])
BASE_URL: str = "https://yifysubtitles.org"
SUBTITLES_URL: str = f"{BASE_URL}/movie-imdb"

session: Session = requests.Session()


def log(module: str, msg: str):
    xbmc.log(f"{__scriptname__}::{module} - {msg}", level=xbmc.LOGINFO)


def search(video: dict, languages: list):
    url = f"{SUBTITLES_URL}/{video['imdb']}"

    log(search.__name__, f"Subtitle url: {url}")
    data = session.get(url).text
    try:
        soup = BeautifulSoup(data, "html.parser")
    except Exception as error:
        return log(search.__name__, f"Failed to parse html: {error}")

    table = soup.find("tbody")
    rows = table.findAll("tr")
    log(search.__name__, f"Found {len(rows)} subtitle(s)")

    for row in rows:
        cells = row.findAll("td")

        language = cells[1].find('span', {'class': 'sub-lang'}, text=True).get_text().split(' ')[0]

        if any(language.lower() in s.lower() for s in languages):
            filename = cells[2].find('a')
            filename.find('span').extract()
            subtitle = {
                'language': language,
                'flag': cells[1].find('span', {'class': 'flag'})['class'][1].replace('flag-', ''),
                'filename': filename.get_text('|', strip=True),
                'link': f"{BASE_URL}{(cells[2].find('a', href=True)['href']).replace('subtitles', 'subtitle')}.zip"
            }

            list_item = xbmcgui.ListItem(label=subtitle['language'], label2=subtitle['filename'])
            list_item.setArt({'thumb': subtitle['flag']})

            url = f"plugin://{__scriptid__}/?action=download&link={subtitle['link']}"
            xbmcplugin.addDirectoryItem(handle=HANDLE, url=url, listitem=list_item, isFolder=False)


def download(url: str):
    log(download.__name__, f"Downloading subtitle: {url}")

    if not os.path.exists(__temp__):
        os.mkdir(__temp__)

    subtitle_list = []
    exts = (".srt", ".sub", ".smi", ".ssa", ".ass", ".sup")
    archive_exts = (".zip", ".rar")

    try:
        log(__name__, "Download Using HTTP")
        subfile = os.path.join(__temp__, url.split('/')[-1])
        r = requests.get(url, stream=True)

        with open(subfile, "wb") as file:
            for chunk in r.iter_content(chunk_size=128):
                file.write(chunk)
        file.close()
    except Exception as error:
        return log(download.__name__, f"Fail to download: {error}")

    if subfile.endswith(exts):
        subtitle_list.append(subfile)

    if subfile.endswith(archive_exts):
        archive_path, file_list = unpack(subfile)

        if len(file_list) == 1:
            subtitle_list.append(os.path.join(archive_path, file_list[0]).replace('\\', '/'))

        if len(file_list) > 1:
            sel = xbmcgui.Dialog().select(heading='Select 1 subtitle', list=file_list, preselect=0)
            subtitle_list.append(os.path.join(archive_path, file_list[sel]).replace('\\', '/'))
    else:
        xbmc.executebuiltin(f'Notification({__scriptname__}, {"Unsupported file"})')
        return log(download.__name__, f"Unsupported file: {subfile}")

    return subtitle_list


def unpack(file_path):
    exts = (".srt", ".sub", ".smi", ".ssa", ".ass", ".sup")

    archive_file = parse.quote_plus(xbmcvfs.translatePath(file_path))
    ext = os.path.splitext(archive_file)[1][1:]
    archive_path = f'{ext}://{archive_file}'

    dirs, files = xbmcvfs.listdir(archive_path)
    subtitle_list = []
    for subfile in files:
        if subfile.endswith(exts):
            subtitle_list.append(subfile)
    return archive_path, subtitle_list


def parse_argv(argv: list) -> dict:
    log(parse_argv.__name__, f"Parsing arguments: {argv}")

    param = dict(parse.parse_qsl(sys.argv[2].lstrip('?')))

    if 'languages' in param:
        param['languages'] = param['languages'] \
            .replace('original',
                     xbmc.convertLanguage(xbmc.getInfoLabel("VideoPlayer.AudioLanguage"), xbmc.ENGLISH_NAME)) \
            .replace('default',
                     xbmc.convertLanguage(xbmc.getInfoLabel("System.Language"), xbmc.ENGLISH_NAME)).split(',')

    log(parse_argv.__name__, f"Parsed arguments: {param}")
    return param


def get_video_info() -> dict:
    log(get_video_info.__name__, f"Fetching meta info")

    video: dict = {'year': xbmc.getInfoLabel("VideoPlayer.Year"),
                   'title': xbmc.getInfoLabel("VideoPlayer.Title"),
                   'imdb': xbmc.getInfoLabel("VideoPlayer.IMDBNumber"),
                   'file_path': parse.unquote(xbmc.Player().getPlayingFile())}

    log(get_video_info.__name__, f"Meta info: {video}")
    return video


def main():
    params: dict = parse_argv(sys.argv)

    video: dict = get_video_info()
    if params['action'] == 'search':
        search(video, params['languages'])

    if params['action'] == 'download':
        subs = download(params["link"])
        for sub in subs:
            listitem = xbmcgui.ListItem(label=sub)
            xbmcplugin.addDirectoryItem(handle=HANDLE, url=sub, listitem=listitem, isFolder=False)

    xbmcplugin.endOfDirectory(HANDLE)


if __name__ == "__main__":
    main()
