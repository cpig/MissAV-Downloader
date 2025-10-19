import logging

import sqlite_conn
import utils_http

class Movie:
    def __init__(self, movie_id: str, source: str):
        logging.info("Initializing Movie with ID: %s", movie_id)
        self.movie_id = movie_id
        self.movie_title = ""
        self.movie_short_url = ""
        self.movie_m3u8_url = ""
        self.movie_reso_playlists = {}
        self.has_1080p = False
        self.has_720p = False
        self.has_480p = False
        self.has_360p = False
        self.playlist_m3u8_url = ""
        self.status = "waiting"
        if source == "internet":
            logging.info("Getting movie info from internet")
            self.get_movie_info_from_internet()
        elif source == "database":
            logging.info("Getting movie info from SQLite")
            self.get_movie_info_from_db()
        return
    
    def get_movie_info_from_internet(self):
        self.movie_short_url = utils_http.get_url_from_id(self.movie_id)
        movie_html = utils_http.get_html_from_url(self.movie_short_url)
        self.movie_title = utils_http.get_movie_title_from_html(movie_html)
        self.movie_m3u8_url = utils_http.get_movie_m3u8_from_html(movie_html)
        self.movie_reso_playlists = utils_http.parse_movie_m3u8(
            utils_http.get_html_from_url(self.movie_m3u8_url))
        self.has_1080p = 1080 in self.movie_reso_playlists
        self.has_720p = 720 in self.movie_reso_playlists
        self.has_480p = 480 in self.movie_reso_playlists
        self.has_360p = 360 in self.movie_reso_playlists
        self.playlist_m3u8_url, _ = utils_http.get_best_resolution_video_m3u8(
            self.movie_reso_playlists)
    
    def get_movie_info_from_db(self):
        ...
    
    def set_movie_info_to_db(self):
        ...

    def change_status(self, new_status):
        self.status = new_status