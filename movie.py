"""
Movie class to represent a MissAV movie object.
Can be initialized from internet or database.
Methods include fetching movie info, inserting/updating movie info to database, etc.
Author: c_pig8828@163.com
Date: 2025-12-24
"""
import logging

import sqlite_conn
import utils_http

class Movie:
    '''
    Movie class to represent a movie object.
    Can be initialized from internet or database.
    '''
    def __init__(self, movie_id: str, source: str, url: str = None):
        logging.info("Initializing Movie %s from %s", movie_id, source)
        self.movie_id = movie_id
        self.movie_title = ""
        self.movie_short_url = ""
        if url:
            self.movie_short_url = url
        self.movie_m3u8_url = ""
        self.movie_reso_playlists = {}
        self.resolutions = {"has_1080p": False, "has_720p": False,
                            "has_480p": False, "has_360p": False}
        self.playlist_m3u8_url = ""
        self.status = "waiting"
        if source == "internet":
            logging.info("Getting movie info from internet")
            self.get_movie_info_from_internet(url=url)
        elif source == "database":
            if not is_movie_id_in_db(self.movie_id):
                raise KeyError(f"Movie {self.movie_id} does not exist in DB.")
            logging.debug("Getting movie info from SQLite")
            self.get_movie_info_from_db()
            if (not self.movie_title) or (not self.playlist_m3u8_url) or (not self.movie_m3u8_url):
                logging.error("Movie ID %s info incomplete in database.", self.movie_id)
                logging.info("Fetching movie info from internet instead.")
                self.get_movie_info_from_internet()
                self.update_movie_to_db()
                logging.debug("Updated movie info in database.")

    def print(self):
        '''
        Print the movie information in a formatted way.
        '''
        print(f"-------- INFO CARD OF {self.movie_id.upper()} --------")
        print(f"Movie Title: \t{self.movie_title}")
        print(f"Short URL: \t{self.movie_short_url}")
        print(f"Movie M3U8: \t{self.movie_m3u8_url}")
        print(f"Best Reso: \t{self.playlist_m3u8_url}")
        print(f"Status: \t{self.status}")
        print("----------------------------------------")

    def get_movie_info_from_internet(self, url=None):
        '''
        Crawl movie info from internet given movie_id
        Store into current movie object.
        '''
        self.movie_short_url = utils_http.get_url_from_id(self.movie_id)
        if not url:
            movie_html = utils_http.get_html_from_url(self.movie_short_url)
        else:
            movie_html = utils_http.get_html_from_url(url)
        self.movie_title = utils_http.get_movie_title_from_html(movie_html)
        self.movie_m3u8_url = utils_http.get_movie_m3u8_from_html(movie_html)
        self.movie_reso_playlists = utils_http.parse_movie_m3u8(
            utils_http.get_html_from_url(self.movie_m3u8_url))
        for reso in [1080, 720, 480, 360]:
            if reso in self.movie_reso_playlists:
                self.resolutions[f"has_{reso}p"] = True
        self.playlist_m3u8_url, _ = utils_http.get_best_resolution_video_m3u8(
            self.movie_reso_playlists)

    def get_movie_info_from_db(self):
        '''
        Get movie info from database given movie_id
        Store into current movie object.
        '''
        conn = sqlite_conn.SqliteConn()
        movie_info = conn.get_movie_info_by_id(self.movie_id)
        self.movie_title = movie_info["movie_title"]
        self.movie_short_url = movie_info["url_short"]
        self.status = movie_info["status"]
        self.playlist_m3u8_url = movie_info["playlist_m3u8"]
        for reso in [1080, 720, 480, 360]:
            self.resolutions[f"has_{reso}p"] = bool(movie_info[f"has_{reso}p"])
        self.movie_m3u8_url = movie_info["movie_m3u8"]
        conn.close()

    def insert_movie_to_db(self):
        '''
        Insert the current movie object into the database.
        '''
        if is_movie_id_in_db(self.movie_id):
            logging.error("Movie %s already exists in database. Skip inserting.", self.movie_id)
            self.get_movie_info_from_db()
            self.print()
            return
        conn = sqlite_conn.SqliteConn()
        conn.insert_movie(self.movie_id, self.movie_title, self.movie_short_url,
                          self.status, self.playlist_m3u8_url, self.resolutions,
                          self.movie_m3u8_url)
        logging.debug("Inserted movie ID %s into database", self.movie_id)
        conn.close()

    def update_movie_to_db(self):
        '''
        Update the current movie object into the database.
        '''
        conn = sqlite_conn.SqliteConn()
        conn.update_movie(self.movie_id, self.movie_title, self.movie_short_url,
                          self.status, self.playlist_m3u8_url, self.resolutions,
                          self.movie_m3u8_url)
        logging.debug("Updated movie ID %s into database", self.movie_id)
        conn.close()

    def change_status(self, new_status):
        '''
        Change the movie status and update the database.
        '''
        self.status = new_status
        conn = sqlite_conn.SqliteConn()
        conn.update_movie_status(self.movie_id, self.status)
        conn.close()

def is_movie_id_in_db(movie_id: str) -> bool:
    '''
    Check if a movie ID exists in the database.
    '''
    logging.debug("Checking if movie ID %s exists in database", movie_id)
    conn = sqlite_conn.SqliteConn()
    exists = conn.is_movie_id_exist(movie_id)
    if exists:
        logging.debug("Movie ID %s exists in database", movie_id)
    else:
        logging.debug("Movie ID %s does not exist in database", movie_id)
    conn.close()
    return exists

def delete_movie_from_db(movie_id: str):
    '''
    Delete a movie from the database by its movie ID.
    '''
    logging.warning("Deleting movie ID %s from database", movie_id)
    conn = sqlite_conn.SqliteConn()
    conn.delete_movie_by_id(movie_id)
    logging.info("Deleted movie ID %s from database", movie_id)
    conn.delete_movie_seg_table(movie_id)
    logging.info("Deleted movie segment table %s from database", movie_id)
    conn.close()
