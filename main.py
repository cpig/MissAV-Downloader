"""
"""

import argparse
import logging

import movie
from movie import Movie
# import sqlite_conn
import task_schedule
import utils_http

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(lineno)d: %(message)s')

def add_movie(movie_id):
    movie = Movie(movie_id, source="internet")
    movie.insert_movie_to_db()

def change_movie_status(movie_id, new_status):
    movie = Movie(movie_id, source="database")
    movie.change_status(new_status)

def download_movie_single(movie_id):
    task_schedule.download_movie(movie_id)

def download_movie_batch():
    task_schedule.download_movies_pending()

parser = argparse.ArgumentParser()
parser.add_argument('action', type=str,
                    choices=['add', 'download', 'list', 'boost', 'change', 'delete'],
                    help='add, download, list, boost')
parser.add_argument('-i', '--id', type=str, help='movie id, e.g. sone-499')
parser.add_argument('-c', '--change', type=str, choices=['waiting', 'finished'],
                    help='force to re-download or mark as finished')
args = parser.parse_args()
if args.action in ("add", "delete", "boost", "change") and not args.id:
    parser.error("The following arguments are required: -i/--id")

# 新增待下载电影
if args.action == "add":
    add_movie(args.id)

# 修改movie下载状态，如从waiting变为finished
if args.action == "change":
    if not args.change:
        parser.error("The following arguments are required: -c/--change")
    change_movie_status(args.id, args.change)

if args.action == "list":
    # 展示单条movie信息
    if args.id:
        if movie.is_movie_id_in_db(args.id):
            movie_obj = Movie(args.id, source="database")
            movie_obj.print()
    else:
        ...

if args.action == "delete":
    movie.delete_movie_from_db(args.id)

if args.action == "download":
    # 下载单个电影
    if args.id:
        if not movie.is_movie_id_in_db(args.id):
            logging.error("Movie ID %s not found in database", args.id)
            add_movie(args.id)
        download_movie_single(args.id)
    # 批量下载电影
    else:
        download_movie_batch()
