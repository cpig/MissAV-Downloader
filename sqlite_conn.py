""" 
Use SQLite database to store the downloader tasks.
Table 'movies' stores all the movie downloaded or to be downloaded.
When downloading a specific movie, a movie-level table is created to 
store the file segments of each movie.
Author: c_pig8828@163.com
Date: 2025-12-24
"""
import datetime
import logging
import sqlite3

import config

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s: %(message)s')

class SqliteConn:
    """
    SQLite connection class to handle all database operations.
    Including: movie-list table CRUD, movie-level segment table CRUD.
    """
    def __init__(self):
        """
        Initialize the SQLite connection and create the core table if not exists.
        """
        logging.debug("Connecting to SQLite database 'missav.db' ...")
        self.conn = sqlite3.connect(config.SQLITE_DB_PATH)
        self.cursor = self.conn.cursor()
        table_list = self.get_tables()
        if 'movies' not in table_list:
            logging.warning("Table 'movies' not found, creating it.")
            self.create_movie_table()
        logging.debug("Connected to database.")

    def create_movie_table(self):
        """
        Create the core table to store all the movie information.
        """
        self.cursor.execute(\
                '''CREATE TABLE IF NOT EXISTS 
                   movies (
                    movie_id TEXT PRIMARY KEY,
                    movie_title TEXT,
                    url_short TEXT,
                    url_long TEXT,
                    status TEXT
                   )
                ''')
        self.conn.commit()
        logging.info("Table 'movies' created.")

    def create_movie_seg_table(self, movie_id, ts_list):
        """
        Create a movie-level table to store all the segments of a specific movie."""
        movie_id = movie_id.replace('-', '_')
        self.cursor.execute(\
                f'''CREATE TABLE IF NOT EXISTS 
                    movie_seg_{movie_id} (
                    seg_id INT PRIMARY KEY,
                    url TEXT,
                    local_path TEXT,
                    status TEXT
                   )
                ''')
        self.conn.commit()
        logging.debug("Table movie_segs for %s created.", movie_id)

        sql_multiple_insert = f"""INSERT INTO movie_seg_{movie_id} (seg_id, url, status) VALUES """
        for i, item in enumerate(ts_list):
            sql_multiple_insert += f"({i+1}, '{item}', 'waiting'),"
        sql_multiple_insert = sql_multiple_insert[:-1] + ";"
        self.cursor.execute(sql_multiple_insert)
        self.conn.commit()
        logging.debug("Inserted %d segments into movie_seg_%s table.", len(ts_list), movie_id)

    def delete_movie_seg_table(self, movie_id):
        """
        Delete the movie-level segment task table."""
        self.cursor.execute(\
            f'''DROP TABLE movie_seg_{movie_id.replace('-', '_')}''')
        self.conn.commit()
        logging.debug("Deleted movie_seg_%s table.", movie_id)
        self.cursor.execute('''VACUUM''')
        self.conn.commit()

    def get_segments_by_status(self, movie_id, status=None):
        """
        Get movie segments for downloading tasks.
        """
        if not status:
            self.cursor.execute(\
                f'''SELECT seg_id, url, local_path
                    FROM movie_seg_{movie_id.replace('-', '_')}''')
        elif not status in ('waiting', 'finished'):
            logging.error("Invalid segment status: %s", status)
            return None
        else:
            self.cursor.execute(\
                f'''SELECT seg_id, url, local_path
                    FROM movie_seg_{movie_id.replace('-', '_')}
                    WHERE status = '{status}' ''')
        return self.cursor.fetchall()

    def update_segment_status(self, movie_id, seg_id, new_status, local_path=""):
        """
        Update the status of a specific segment."""
        retry_cnt = 0
        while retry_cnt <= 3:
            try:
                self.cursor.execute(\
                f'''UPDATE movie_seg_{movie_id.replace('-', '_')} 
                    SET status=?, local_path=? WHERE seg_id=?''',
                (new_status, local_path, seg_id))
                self.conn.commit()
                break
            except sqlite3.OperationalError as e:
                logging.error("SQLite OperationalError: %s. Retrying %d/3...",
                              str(e), retry_cnt+1)
                retry_cnt += 1
                if retry_cnt > 3:
                    raise e
        return self

    def get_tables(self):
        """
        Get all the table names in the database.
        """
        self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        table_records = self.cursor.fetchall()
        return list(map(lambda x: x[0], table_records))

    def insert_movie(self, movie_id, title, short_url, status, playlist_m3u8, 
                     resolution_dict, movie_m3u8_url):
        """
        Insert a new movie to be downloaded into the movies table.
        """
        if self.is_movie_id_exist(movie_id):
            logging.error("Movie ID %s already exists in database, skipping insert.",
                           movie_id)
            return
        cur_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.cursor.execute(\
            '''INSERT INTO movies 
               (movie_id, movie_title, url_short, status, playlist_m3u8, 
                has_1080p, has_720p, has_480p, has_360p, movie_m3u8, refresh_time)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (movie_id, title, short_url, status,
             playlist_m3u8, resolution_dict["has_1080p"], resolution_dict["has_720p"],
             resolution_dict["has_480p"], resolution_dict["has_360p"],
             movie_m3u8_url, cur_time))
        self.conn.commit()
        logging.debug("Inserted movie ID %s into database.", movie_id)
        return

    def update_movie(self, movie_id, title, short_url, status, playlist_m3u8,
                     resolution_dict, movie_m3u8_url):
        """
        Insert a new movie to be downloaded into the movies table.
        """
        if not self.is_movie_id_exist(movie_id):
            logging.error("Movie ID %s does not exist in database, skipping update.",
                          movie_id)
            return
        cur_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.cursor.execute(\
            '''UPDATE movies 
            SET movie_title=?, url_short=?, status=?, playlist_m3u8=?, 
            has_1080p=?, has_720p=?, has_480p=?, has_360p=?, movie_m3u8=?, refresh_time=?
            WHERE movie_id = ?''',
            (title, short_url, status,
             playlist_m3u8, resolution_dict["has_1080p"], resolution_dict["has_720p"],
             resolution_dict["has_480p"], resolution_dict["has_360p"],
             movie_m3u8_url, cur_time, movie_id))
        self.conn.commit()
        logging.debug("Updated movie ID %s into database.", movie_id)
        return

    def update_movie_status(self, movie_id, new_status):
        """"
        Change only status instead of whole movie info update."""
        cur_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.cursor.execute(\
            '''UPDATE movies 
            SET status=?, refresh_time=?
            WHERE movie_id = ?''',
            (new_status, cur_time, movie_id))
        self.conn.commit()
        logging.debug("Updated movie ID %s status=%s into database.", movie_id, new_status)

    def get_movie_info_by_id(self, movie_id):
        """
        Get the movie information by its movie_id.
        """
        self.cursor.execute(\
            '''SELECT * FROM movies WHERE movie_id = ?''', (movie_id,))
        movie_row = self.cursor.fetchone()
        return {"movie_id": movie_row[0],
                "movie_title": movie_row[1],
                "url_short": movie_row[2],
                "url_long": movie_row[3],
                "status": movie_row[4],
                "playlist_m3u8": movie_row[5],
                "has_360p": movie_row[6],
                "has_480p": movie_row[7],
                "has_720p": movie_row[8],
                "has_1080p": movie_row[9],
                "movie_m3u8": movie_row[10],
                "refresh_time": movie_row[11]
                }

    def get_movie_by_status(self, status, is_id_only=False):
        """
        Get the movie_id of the movie under a specific status.
        """
        self.cursor.execute(\
            '''SELECT movie_id, movie_title FROM movies WHERE status = ? ''', (status,))
        records = self.cursor.fetchall()
        logging.info("Found %d movies with status %s.", len(records), status)
        if is_id_only:
            return [record[0] for record in records]
        return records

    def get_movie_by_keyword(self, keyword):
        """
        Get the movie_id of the movie with a specific keyword.
        """
        self.cursor.execute(\
            '''SELECT movie_id, status, movie_title FROM movies WHERE movie_title LIKE ? ''', 
            (f'%{keyword}%',))
        records = self.cursor.fetchall()
        logging.info("Found %d movies with keyword %s.", len(records), keyword)
        return records

    def is_movie_id_exist(self, movie_id):
        """
        Check if a movie with the given movie_id exists in the movies table.
        """
        self.cursor.execute(\
            '''SELECT COUNT(*) FROM movies WHERE movie_id = ?''', (movie_id,))
        count = self.cursor.fetchone()[0]
        return count > 0

    def delete_movie_by_id(self, movie_id):
        """
        Delete a movie from the movies table by its movie_id.
        """
        self.cursor.execute(\
            '''DELETE FROM movies WHERE movie_id = ?''', (movie_id,))
        self.conn.commit()
        logging.info("Deleted movie ID %s from database.", movie_id)

    def close(self):
        """Close the connection."""
        self.conn.close()
