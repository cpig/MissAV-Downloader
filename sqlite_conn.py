""" 
Use SQLite database to store the downloader tasks.
Table 'movies' stores all the movie downloaded or to be downloaded.
When downloading a specific movie, a movie-level table is created to 
store the file segments of each movie.
Author: c_pig8828@163.com
Date: 2025-09-24
"""
import logging
import sqlite3
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(lineno)d: %(message)s')

class SqliteConn:
    def __init__(self):
        """
        Initialize the SQLite connection and create the core table if not exists.
        """
        logging.info("Connecting to SQLite database 'missav.db' ...")
        self.conn = sqlite3.connect('missav.db')
        self.cursor = self.conn.cursor()
        table_list = self.get_tables()
        if 'movies' not in table_list:
            logging.warning("Table 'movies' not found, creating it.")
            self.create_movie_table()
        logging.info("Connected to database.")
        return
        #self.cursor.execute("CREATE TABLE IF NOT EXISTS video (id INTEGER PRIMARY KEY, url TEXT)")
        #self.conn.commit()

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

    def create_movie_seg_table(self, movie_id):
        pass

    def get_tables(self):
        """
        Get all the table names in the database.
        """
        self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        table_records = self.cursor.fetchall()
        return list(map(lambda x: x[0], table_records))

    def insert_movie(self, movie_id, movie_title, url_short, url_long, status):
        """
        Insert a new movie to be downloaded into the movies table.
        """
        self.cursor.execute(\
            '''INSERT INTO movies (movie_id, movie_title, url_short, url_long, status)
               VALUES (?, ?, ?, ?, ?)''',
               (movie_id, movie_title, url_short, url_long, status))
        self.conn.commit()

    def insert(self, url):
        self.cursor.execute("INSERT INTO video (url) VALUES (?)", (url,))
        self.conn.commit()

    def close(self):
        self.conn.close()