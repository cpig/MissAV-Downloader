""" 
Use SQLite database to store the downloader tasks.
Table 'movies' stores all the movie downloaded or to be downloaded.
When downloading a specific movie, a movie-level table is created to 
store the file segments of each movie.
Author: c_pig8828@163.com
Date: 2025-09-24
"""
import datetime
import logging
import sqlite3

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(lineno)d: %(message)s')

class SqliteConn:
    def __init__(self):
        """
        Initialize the SQLite connection and create the core table if not exists.
        """
        logging.debug("Connecting to SQLite database 'missav.db' ...")
        self.conn = sqlite3.connect('missav.db')
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
        logging.info("Table movie_segs for %s created.", movie_id)

        sql_multiple_insert = f"""INSERT INTO movie_seg_{movie_id} (seg_id, url, status) VALUES """
        for i, item in enumerate(ts_list):
            sql_multiple_insert += f"({i+1}, '{item}', 'waiting'),"
        sql_multiple_insert = sql_multiple_insert[:-1] + ";"
        self.cursor.execute(sql_multiple_insert)
        self.conn.commit()
        logging.info("Inserted %d segments into movie_seg_%s table.", len(ts_list), movie_id)
    
    def get_waiting_segments_for_movie(self, movie_id):
        self.cursor.execute(\
            f'''SELECT seg_id, url FROM movie_seg_{movie_id.replace('-', '_')}         
                WHERE status = 'waiting' ''')
        return self.cursor.fetchall()
    
    def update_segment_status(self, movie_id, seg_id, new_status, local_path=""):
        self.cursor.execute(\
            f'''UPDATE movie_seg_{movie_id.replace('-', '_')} 
                SET status=?, local_path=? WHERE seg_id=?''',
            (new_status, local_path, seg_id))
        self.conn.commit()

    def get_tables(self):
        """
        Get all the table names in the database.
        """
        self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        table_records = self.cursor.fetchall()
        return list(map(lambda x: x[0], table_records))

    def insert_movie(self, movie_id, title, short_url, status, playlist_m3u8,
                     has_1080p, has_720p, has_480p, has_360p, movie_m3u8_url):
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
             playlist_m3u8, has_1080p, has_720p, has_480p,
             has_360p, movie_m3u8_url, cur_time))
        self.conn.commit()
        logging.info("Inserted movie ID %s into database.", movie_id)
        return

    def update_movie(self, movie_id, title, short_url, status, playlist_m3u8,
                     has_1080p, has_720p, has_480p, has_360p, movie_m3u8_url):
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
             playlist_m3u8, has_1080p, has_720p, has_480p,
             has_360p, movie_m3u8_url, cur_time, movie_id))
        self.conn.commit()
        logging.info("Updated movie ID %s into database.", movie_id)
        return

    def update_movie_status(self, movie_id, new_status):
        """"Change only status instead of whole movie info update."""
        cur_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.cursor.execute(\
            '''UPDATE movies 
            SET status=?, refresh_time=?
            WHERE movie_id = ?''',
            (new_status, cur_time, movie_id))
        self.conn.commit()
        logging.info("Updated movie ID %s status=%s into database.", movie_id, new_status)

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

    def count_waiting_movies(self):
        """
        Count how many movies are in 'waiting' status.
        """
        self.cursor.execute(\
            '''SELECT COUNT(*) FROM movies WHERE status = 'waiting' ''')
        count = self.cursor.fetchone()[0]
        return count

    def get_waiting_movie_ids(self):
        """
        Get the movie_id of the movie which is currently 'waiting'.
        """
        self.cursor.execute(\
            '''SELECT movie_id FROM movies WHERE status = 'waiting' ''')
        records = self.cursor.fetchall()
        return [record[0] for record in records]

    def get_downloading_movie_id(self):
        """
        Get the movie_id of the movie which is currently 'downloading'.
        """
        self.cursor.execute(\
            '''SELECT movie_id FROM movies WHERE status = 'downloading' ''')
        records = self.cursor.fetchall()
        return [record[0] for record in records]

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
