"""
"""

import argparse
import logging

from movie import Movie
import movie_downloader
import sqlite_conn
import utils_http

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(lineno)d: %(message)s')

parser = argparse.ArgumentParser()
parser.add_argument('action', type=str, choices=['add', 'download', 'list', 'boost', 'change'],
                    help='add, download, list, boost')
parser.add_argument('-i', '--id', type=str, help='movie id, e.g. sone-499')
parser.add_argument('-c', '--change', type=str, choices=['waiting', 'finished'],
                    help='force to re-download or mark as finished')
args = parser.parse_args()
if args.action == "download" and not args.id:
    parser.error("the following arguments are required for 'download': -i/--id")

print(args.action)
print(args.id)

sql_conn = sqlite_conn.SqliteConn()

def add_movie(movie_id):
    movie = Movie(movie_id, source="internet")
    movie.set_movie_info_to_db()