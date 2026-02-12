"""
Main entry point for MissAV Downloader.
Supports adding movies, downloading movies, listing movies,
changing movie status and deleting movies.

TO-DO LIST:
1. 下载后发现不完整的情况
2. list全部影片信息的功能
"""
import argparse
import logging

import movie
from movie import Movie
import sqlite_conn
import task_schedule
import utils_file

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s: %(message)s')
#                    format='%(asctime)s - %(levelname)s - %(lineno)d: %(message)s')

parser = argparse.ArgumentParser()
parser.add_argument('action', type=str,
                    choices=['add', 'download', 'list', 'change', 'delete'],
                    help='add, download, list, change, delete')
parser.add_argument('-i', '--id', type=str,
                    help='Movie id, e.g. sone-499. Supports multiple IDs separated by comma.')
parser.add_argument('-k', '--keyword', type=str,
                    help='keyword to help search, e.g. sone, 愛才りあ, イキ')
parser.add_argument('-s', '--status', type=str, choices=['waiting', 'finished', 'downloading'],
                    help='force to re-download or mark as finished')
parser.add_argument('-u', '--url', type=str,
                    help='Movie url (forced), e.g. https://www.missav.com/sone-499')
args = parser.parse_args()
if args.action in ("add", "delete", "boost", "change") and not args.id:
    parser.error("The following arguments are required: -i/--id")

# 新增待下载电影
if args.action == "add":
    if not args.id:
        parser.error("The following arguments are required: -i/--id")
    id_list = args.id.split(",")
    for movie_id in id_list:
        movie = Movie(movie_id, source="internet")
        movie.insert_movie_to_db()

# 修改movie下载状态，如从waiting变为finished
if args.action == "change":
    if not args.status:
        parser.error("The following arguments are required: -s/--status")
    movie = Movie(args.id, source="database")
    movie.change_status(args.change)

if args.action == "list":
    # 展示单条movie信息
    if args.id:
        if movie.is_movie_id_in_db(args.id):
            movie_obj = Movie(args.id, source="database")
            movie_obj.print()
        else:
            logging.error("Movie ID %s not found in database", args.id)
    # 按状态和关键词查找
    # elif args.status and args.keyword:
    #    logging.info("Listing movie with status=%s and keyword=%s", args.status, args.keyword)
    elif args.status:
        logging.info("Listing all the movie with status=%s", args.status)
        if args.keyword:
            logging.info("AND filter by keyword=%s", args.keyword)
        conn = sqlite_conn.SqliteConn()
        listing_movies = conn.get_movie_by_status(args.status)
        for movie in listing_movies:
            if args.keyword and (args.keyword not in movie[1]):
                continue
            print(movie[0]+"\t"+movie[1])
    elif args.keyword:
        logging.info("Listing all the movie with keyword=%s", args.keyword)
        conn = sqlite_conn.SqliteConn()
        listing_movies = conn.get_movie_by_keyword(args.keyword)
        stat = {"waiting": 0, "finished": 0, "downloading": 0}
        for movie in listing_movies:
            stat[movie[1]] += 1
            print(movie[0] + "\t" + movie[1] + "\t" + movie[2])
        logging.info("Summary: %s", stat)
    else:
        logging.info("Count movies in database")
        conn = sqlite_conn.SqliteConn()
        stat = {"waiting": len(conn.get_movie_by_status("waiting")), 
                "finished": len(conn.get_movie_by_status("finished")), 
                "downloading": len(conn.get_movie_by_status("downloading"))}
        logging.info("Summary: %s", stat)

if args.action == "delete":
    movie.delete_movie_from_db(args.id)
    logging.info("Movie deleted from DB.")
    utils_file.delete_movie_dir(args.id)
    logging.info("Movie files deleted.")

if args.action == "download":
    # 下载单个电影
    if args.id:
        if not movie.is_movie_id_in_db(args.id):
            logging.error("Movie ID %s not found in database", args.id)
            movie = Movie(args.id, source="internet", url=args.url)
            movie.insert_movie_to_db()
        task_schedule.download_movie(args.id)
    # 批量下载电影
    else:
        task_schedule.download_movies_pending()
