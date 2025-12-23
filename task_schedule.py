import logging
import os
import queue
import threading

import config
import movie
import sqlite_conn
import utils_http

queue_lock = threading.Lock()
finish_lock = threading.Lock()

def get_movie_id_to_download():
    conn = sqlite_conn.SqliteConn()
    downloading_movies = conn.get_downloading_movie_id()
    if downloading_movies:
        logging.info("Got a downloading movie: %s", downloading_movies[0])
        conn.close()
        return downloading_movies[0]
    waiting_movies = conn.get_waiting_movie_ids()
    if waiting_movies:
        logging.info("Got a waiting movie: %s", waiting_movies[0])
        conn.close()
        return waiting_movies[0]
    conn.close()
    logging.info("No movie to download.")
    return None

def create_movie_segment_tasks(movie_to_download: movie.Movie):
    logging.info("Getting segment list M3U8 file for movie ID %s", movie_to_download.movie_id)
    playlist_folder = utils_http.get_path_folder(movie_to_download.movie_m3u8_url)
    video_m3u8_filename = movie_to_download.playlist_m3u8_url
    video_m3u8_url = f"{playlist_folder}/{video_m3u8_filename}"
    segments_subfolder = utils_http.get_path_folder(video_m3u8_url)
    logging.info("Movie M3U3 URL: %s", video_m3u8_url)
    movie_ts_list = utils_http.get_video_ts_from_video_m3u8(
                        utils_http.get_html_from_url(video_m3u8_url), segments_subfolder)
    conn = sqlite_conn.SqliteConn()
    conn.create_movie_seg_table(movie_id=movie_to_download.movie_id, ts_list=movie_ts_list)
    conn.close()

def download_movie_segment(segment_queue: queue.Queue, finished_queue: queue.Queue, movie_id: str):
    while not segment_queue.empty():
        with queue_lock:
            seg_id, seg_url = segment_queue.get()
        local_path = f"{movie_id}/{seg_id:06d}.ts"
        try:
            utils_http.download_single_segment(seg_url, local_path)
            logging.info("Downloaded segment %d", seg_id)
            conn = sqlite_conn.SqliteConn()
            conn.update_segment_status(movie_id, seg_id, "finished", local_path)
            conn.close()
            # finished_queue.put(seg_id)
        except Exception as e:
            logging.error("Error downloading segment %d: %s", seg_id, str(e))
            with queue_lock:
                segment_queue.put((seg_id, seg_url))

class SegmentDownloadThread(threading.Thread):
    def __init__(self, thread_name,segment_queue: queue.Queue,
                 finished_queue: queue.Queue, movie_id: str):
        threading.Thread.__init__(self)
        self.name = thread_name
        self.segment_queue = segment_queue
        self.finished_queue = finished_queue
        self.movie_id = movie_id
        logging.info("Thread %s initialized for movie ID %s", self.name, self.movie_id)

    def run(self):
        download_movie_segment(self.segment_queue, self.finished_queue, self.movie_id)
        logging.info("Thread %s finished for movie ID %s", self.name, self.movie_id)

def download_movie_by_segments(movie_to_download: movie.Movie, num_threads: int=config.THREADS):
    conn = sqlite_conn.SqliteConn()
    segment_records = conn.get_waiting_segments_for_movie(movie_to_download.movie_id)
    segment_queue = queue.Queue()
    finished_queue = queue.Queue()
    for seg_id, seg_url in segment_records:
        segment_queue.put((seg_id, seg_url))
    logging.info("Inserted %i pending tasks into queue", segment_queue.qsize())
    if not os.path.exists(movie_to_download.movie_id):
        os.makedirs(movie_to_download.movie_id)
    logging.info("Creating downloading threads")
    threads = []
    for i in range(num_threads):
        thread = SegmentDownloadThread(thread_name=f"Thread-{i+1}",
                                       segment_queue=segment_queue,
                                       finished_queue=finished_queue,
                                       movie_id=movie_to_download.movie_id)
        thread.start()
        threads.append(thread)
    for thread in threads:
        thread.join()
    #while not finished_queue.empty():
    #    seg_id = finished_queue.get()
    #    conn.update_segment_status(movie_to_download.movie_id, seg_id, "finished")
    conn.close()
    logging.info("All segments downloaded for movie ID %s", movie_to_download.movie_id)

def merge_ts_into_one(movie_to_download: movie.Movie):
    movie_id = movie_to_download.movie_id
    movie_title = movie_to_download.movie_title
    os.system(f"copy /b {movie_id}\\*.ts {movie_title}.ts")
    os.system(f"rmdir /s /q {movie_id}")
    logging.info("Merged all .ts segments into %s.ts", movie_title)

if __name__ == "__main__":
    movie_id_to_download = get_movie_id_to_download()
    logging.info("Get a movie ID to download: %s", movie_id_to_download)
    movie_to_download = movie.Movie(movie_id=movie_id_to_download, source="database")
    movie_to_download.print()
    # create_movie_segment_tasks(movie_to_download=movie_to_download)
    # download_movie_by_segments(movie_to_download=movie_to_download)
    merge_ts_into_one(movie_to_download=movie_to_download)
    movie_to_download.change_status("finished")
    logging.info("Movie ID %s download finished.", movie_id_to_download)