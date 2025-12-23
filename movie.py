import logging

import sqlite_conn
import utils_http

class Movie:
    def __init__(self, movie_id: str, source: str):
        logging.info("Initializing Movie %s from %s", movie_id, source)
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
            if not is_movie_id_in_db(self.movie_id):
                logging.error("Cannot intialize from database, %s does not exist", self.movie_id)
                return
            logging.info("Getting movie info from SQLite")
            self.get_movie_info_from_db()
            if (not self.movie_title) or (not self.playlist_m3u8_url) or (not self.movie_m3u8_url):
                logging.error("Movie ID %s info incomplete in database", self.movie_id)
                logging.info("Fetching movie info from internet instead")
                self.get_movie_info_from_internet()
        return

    def print(self):
        logging.info("Movie ID: %s", self.movie_id)
        logging.info("Movie Title: %s", self.movie_title)
        logging.info("Movie Short URL: %s", self.movie_short_url)
        logging.info("Playlist M3U8 URL: %s", self.playlist_m3u8_url)
        logging.info("Status: %s", self.status)

    def get_movie_info_from_internet(self):
        '''Crawl movie info from internet given movie_id
        Store into current movie object.
        '''
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
        '''Get movie info from database given movie_id
        Store into current movie object.
        '''
        conn = sqlite_conn.SqliteConn()
        movie_info = conn.get_movie_info_by_id(self.movie_id)
        self.movie_title = movie_info["movie_title"]
        self.movie_short_url = movie_info["url_short"]
        self.status = movie_info["status"]
        self.playlist_m3u8_url = movie_info["playlist_m3u8"]
        self.has_1080p = bool(movie_info["has_1080p"])
        self.has_720p = bool(movie_info["has_720p"])
        self.has_480p = bool(movie_info["has_480p"])
        self.has_360p = bool(movie_info["has_360p"])
        self.movie_m3u8_url = movie_info["movie_m3u8"]
        conn.close()

    def insert_movie_to_db(self):
        '''Insert the current movie object into the database.'''
        conn = sqlite_conn.SqliteConn()
        conn.insert_movie(self.movie_id, self.movie_title, self.movie_short_url,
                          self.status, self.playlist_m3u8_url, self.has_1080p,
                          self.has_720p, self.has_480p, self.has_360p,
                          self.movie_m3u8_url)
        # logging.info("Inserted movie ID %s into database", self.movie_id)
        conn.close()

    def update_movie_to_db(self):
        '''Update the current movie object into the database.'''
        conn = sqlite_conn.SqliteConn()
        conn.update_movie(self.movie_id, self.movie_title, self.movie_short_url,
                          self.status, self.playlist_m3u8_url, self.has_1080p,
                          self.has_720p, self.has_480p, self.has_360p,
                          self.movie_m3u8_url)
        logging.info("Updated movie ID %s into database", self.movie_id)
        conn.close()

    def change_status(self, new_status):
        '''Change the movie status and update the database.'''
        self.status = new_status
        conn = sqlite_conn.SqliteConn()
        conn.update_movie_status(self.movie_id, self.status)
        conn.close()

def is_movie_id_in_db(movie_id: str) -> bool:
    '''Check if a movie ID exists in the database.'''
    logging.info("Checking if movie ID %s exists in database", movie_id)
    conn = sqlite_conn.SqliteConn()
    exists = conn.is_movie_id_exist(movie_id)
    if exists:
        logging.info("Movie ID %s exists in database", movie_id)
    else:
        logging.info("Movie ID %s does not exist in database", movie_id)
    conn.close()
    return exists

def delete_movie_from_db(movie_id: str):
    '''Delete a movie from the database by its movie ID.'''
    logging.info("Deleting movie ID %s from database", movie_id)
    conn = sqlite_conn.SqliteConn()
    conn.delete_movie_by_id(movie_id)
    logging.info("Deleted movie ID %s from database", movie_id)
    conn.close()
