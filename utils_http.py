import urllib.request
import re
import logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(lineno)d: %(message)s')

BASE_HEADER = {
    'Accept': 'text/html,application/xhtml+xml,application/xml',
    'Accept-Encoding': 'gzip, deflate, br, zstd',
    'Accept-Language': 'ja-JP,ja;q=0.9,zh-CN;q=0.8,zh;q=0.7,en-US;q=0.6,en;q=0.5'
}
BASE_HEADER_POSTMAN = {
    'User-Agent': 'PostmanRuntime/7.47.1',
    'Accept': '*/*',
    'Cache-Control':'no-cache'}

def get_url_from_id(movie_id):
    """
    Construct the MissAV movie URL from the given movie ID.
    """
    url = f"https://missav.ws/ja/{movie_id}"
    # url = f"https://missav.ws/{movie_id}"
    logging.info("Constructed URL: %s", url)
    return url

def get_html_from_url(url):
    """
    Fetch the HTML content from the given URL.
    """
    # opener = urllib.request.build_opener()
    host = re.findall(r"https?://([^/]+)/", url)[0]
    logging.debug("Host=%s", host)
    # opener.addheaders = [('Host', host)]
    # urllib.request.install_opener(opener)
    headers = BASE_HEADER_POSTMAN.copy()
    headers['Host'] = host
    req = urllib.request.Request(url, headers=headers)
    logging.debug("Request headers=%s", req.headers)
    #req = urllib.request.Request(url, headers={"Host":host})
    logging.info("Fetching HTML from %s", url)
    with urllib.request.urlopen(req) as response:
        result = response.read().decode('utf-8')
        logging.info("HTML length=%d", len(result))
        return result

def get_playlists_m3u8_from_movie_html(html):
    """
    Extract the playlists m3u8 URL from the movie HTML content.
    The URL pattern has to be manually found by the user.
    """
    matched_groups = re.search(r"m3u8\|.+\|video", html)
    matched_string = matched_groups.group(0)
    logging.info("M3U8 matched string: %s", matched_string)
    str_list = matched_string.split('|')
    m3u8_url = f"https://{str_list[7]}.{str_list[6]}/{str_list[5]}-{str_list[4]}-{str_list[3]}-{str_list[2]}-{str_list[1]}/playlist.m3u8"
    logging.info("Constructed playlists m3u8 URL: %s", m3u8_url)
    return m3u8_url

def get_movie_title_from_movie_html(html):
    matched_groups = re.search(r"<h1.*>.*<\/h1>", html)
    matched_string = matched_groups.group(0)
    logging.info("Movie title matched string: %s", matched_string)
    title = matched_string[1:-1].split('>')[1].split('<')[0]
    logging.info("Movie title: %s", title)
    return title

def get_video_m3u8_from_playlists_m3u8(m3u8_txt):
    logging.info("Parsing playlists m3u8 content")
    resolution_path = {}
    lines = m3u8_txt.split('\n')
    resolution_re_pattern = re.compile(r'RESOLUTION=(\d+x\d+)')
    for i, line in enumerate(lines):
        if line.startswith('#'):
            match = resolution_re_pattern.search(line)
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

def get_path_folder(url):
    return url.rsplit('/', 1)[0]

def get_best_resolution_video_m3u8(m3u8_dict):
    best_key = max(list(m3u8_dict.keys()))
    logging.info("Best resolution: %d, file: %s", best_key, m3u8_dict[best_key])
    return m3u8_dict[best_key], best_key

def get_video_ts_from_video_m3u8(m3u8_txt):
    ts_list = []
    lines = m3u8_txt.split('\n')
    for line in lines:
        if line.startswith('#'):
            continue
        else:
            ts_list.append(line.strip())
    logging.info("Total .ts files: %d", len(ts_list))
    return ts_list

html = get_html_from_url(get_url_from_id("sqte-503"))
playlist_m3u8_url = get_playlists_m3u8_from_movie_html(html)
playlist_folder = get_path_folder(playlist_m3u8_url)
movie_title = get_movie_title_from_movie_html(html)
# print(playlist_m3u8_url)

txt = get_html_from_url(playlist_m3u8_url)
m3u8_dict = get_video_m3u8_from_playlists_m3u8(txt)
video_m3u8_filename, best_resolution = get_best_resolution_video_m3u8(m3u8_dict)
video_m3u8_url = f"{playlist_folder}/{video_m3u8_filename}"
# print(video_m3u8_url)
segments_list = get_video_ts_from_video_m3u8(get_html_from_url(video_m3u8_url))
print(segments_list)