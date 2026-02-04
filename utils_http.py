"""
HTTP utility functions for MissAV Downloader.
Includes functions for constructing URLs, fetching HTML content,
parsing m3u8 files, and downloading video segments.
Author: c_pig8828@163.com
Date: 2025-12-24
"""
import logging
import re
import time
import urllib.request

import config
import utils_file
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s: %(message)s')

def parse_host(url):
    """
    Parse the host from the given URL for header building.
    """
    host = re.findall(r"https?://([^/]+)/", url)[0]
    logging.debug("Url=%s, Host=%s", url, host)
    return host

def get_url_from_id(movie_id):
    """
    Construct the MissAV movie URL from the given movie ID.
    """
    url = config.MOVIE_URL_PATTERN.format(movie_id)
    # url = f"https://missav.ws/{movie_id}"
    logging.debug("Constructed URL: %s", url)
    return url

def get_html_from_url(url):
    """
    Fetch the HTML content from the given URL.
    """
    succeed = False
    fail_attempts = 0
    while (not succeed) and fail_attempts < config.HTTP_RETRY_TIMES:
        try:
            headers = config.BASE_HEADER_POSTMAN.copy()
            headers['Host'] = parse_host(url)
            req = urllib.request.Request(url, headers=headers)
            logging.debug("Request headers=%s", req.headers)
            logging.debug("Fetching HTML from %s", url)
            with urllib.request.urlopen(req) as response:
                result = response.read().decode('utf-8')
                logging.debug("HTML length=%d", len(result))
                succeed = True
                return result
        except urllib.error.URLError as e:
            logging.error("ConnectionResetError! Check VPN status! %s", repr(e))
            fail_attempts += 1
            time.sleep(config.HTTP_RETRY_PERIOD)
            logging.info("Retrying to fetch HTML... Attempt %d", fail_attempts)
    raise ConnectionError(f"Failed to fetch HTML: {url}")

def get_movie_m3u8_from_html(page_html):
    """
    On movie play page, there is a embedded m3u8 file path. 
    Playlists of all the resolutions are stored in that m3u8 file.
    We would like to find out the path of the file, and use it to get a best resolution one. 
    The URL pattern has to be manually found by the user, if missAV site upgrade frontend solution.
    """
    matched_groups = re.search(r"m3u8\|.+\|video", page_html)
    matched_string = matched_groups.group(0)
    logging.debug("M3U8 matched string: %s", matched_string)
    s = matched_string.split('|')
    m3u8_url = f"https://{s[7]}.{s[6]}/{s[5]}-{s[4]}-{s[3]}-{s[2]}-{s[1]}/playlist.m3u8"
    logging.debug("Constructed playlists m3u8 URL: %s", m3u8_url)
    return m3u8_url

def get_movie_title_from_html(page_html):
    """
    Extract the movie title from the HTML content.
    The title is displayed right down the video player.
    """
    matched_groups = re.search(r"<h1.*>.*<\/h1>", page_html)
    matched_string = matched_groups.group(0)
    logging.debug("Movie title matched string: %s", matched_string)
    title = matched_string[1:-1].split('>')[1].split('<')[0]
    logging.info("Movie title: %s", title)
    return title

def parse_movie_m3u8(m3u8_txt):
    """
    Parse the playlists m3u8 content to get all the available resolutions and their paths.
    Return a dict: key is resolution height(int), value is the m3u8 file name(str).
    E.g. {360: 'video_360p.m3u8', 720: 'video_720p.m3u8', ...}
    """
    logging.info("Parsing playlists m3u8 content")
    resolution_path = {}
    lines = m3u8_txt.split('\n')
    resolution_re_pattern = re.compile(r'RESOLUTION=(\d+x\d+)')
    for i, line in enumerate(lines):
        if line.startswith('#'):
            match = resolution_re_pattern.search(line)
            # A resolution line
            #EXT-X-STREAM-INF:BANDWIDTH=800000,RESOLUTION=640x360,CODECS="..."
            if match:
                resolution = match.group(0)
                resolution_int = int(resolution.split('x')[1])
                next_line = lines[i+1].strip() if (i+1)<len(lines) else ''
                logging.info("Found resolution: %d, URL: %s", resolution_int, next_line)
                resolution_path[resolution_int] = next_line
        else:
            continue
    logging.info("Available resolutions: %s", list(resolution_path.keys()))
    return resolution_path

def get_path_folder(url:str):
    """
    Get the folder path from the given URL.
    E.g. https://surrit.com/8ee02204-300a-4706-b5dc-d107e8686ebb/360p/playlist.m3u8
    return https://surrit.com/8ee02204-300a-4706-b5dc-d107e8686ebb/360p
    """
    return url.rsplit('/', 1)[0]

def get_best_resolution_video_m3u8(m3u8_dict):
    """
    Get the best resolution video m3u8 file path from the given m3u8 dict."""
    best_key = max(list(m3u8_dict.keys()))
    logging.info("Best resolution: %d, file: %s", best_key, m3u8_dict[best_key])
    return m3u8_dict[best_key], best_key

def get_video_ts_from_video_m3u8(m3u8_txt, ts_file_folder):
    """
    Parse the video m3u8 content to get all the .ts segment file URLs.
    Return a list of .ts file URLs.
    """
    ts_list = []
    lines = m3u8_txt.split('\n')
    for line in lines:
        if line.startswith('#'):
            continue
        if line.strip():
            ts_list.append(ts_file_folder + "/" + line.strip())
    logging.info("Total .ts files: %d", len(ts_list))
    return ts_list

def download_single_segment(ts_url, target_file):
    """
    Download a single .ts segment from the given URL to the target file path.
    """
    logging.debug("Downloading segment from %s to %s", ts_url, target_file)
    headers = config.BASE_HEADER_POSTMAN.copy()
    headers['Host'] = parse_host(ts_url)
    req = urllib.request.Request(ts_url, headers=headers)
    with urllib.request.urlopen(req, timeout=config.HTTP_TIMEOUT) as response:
        utils_file.delete_file(target_file)
        with open(target_file, 'wb') as f:
            f.write(response.read())
    logging.debug("Downloaded segment to %s", target_file)
