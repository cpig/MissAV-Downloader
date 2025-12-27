import logging
import os
import queue
import shutil
import threading
import time
import tqdm

import config
import movie
import sqlite_conn
import utils_http

queue_lock = threading.Lock()
# finish_lock = threading.Lock()

def get_movie_id_to_download():
    """
    Get a movie ID that is pending download. Return None if no movie to download.
    Priority: downloading -> waiting
    """
    conn = sqlite_conn.SqliteConn()
    downloading_movies = conn.get_movie_ids_by_status('downloading')
    if downloading_movies:
        logging.info("Got a downloading movie: %s", downloading_movies[0])
        conn.close()
        return downloading_movies[0]
    waiting_movies = conn.get_movie_ids_by_status('waiting')
    if waiting_movies:
        logging.info("Got a waiting movie: %s", waiting_movies[0])
        conn.close()
        return waiting_movies[0]
    conn.close()
    logging.info("No movie to download.")
    return None

def create_movie_segment_tasks(movie_to_download: movie.Movie):
    """
    Before start downloading movie, create a table in the database to store and track
    every single ts segment download status.
    """
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

class SegmentDownloadThread(threading.Thread):
    """
    Thread definition for downloading movie segments.
    Check if the segment queue is empty, if not then get a task and download, 
    if yes then exit. Therefore the task queue need to be initialized with 
    all tasks before setting up these download threads.
    """
    def __init__(self, thread_name: str, segment_queue: queue.Queue,
                 movie_id: str):
        threading.Thread.__init__(self)
        self.name = thread_name
        self.segment_queue = segment_queue
        self.movie_id = movie_id
        self._force_stop = threading.Event()
        logging.debug("Thread %s initialized for movie ID %s", self.name, self.movie_id)

    def stop(self):
        '''
        Label forced_stop from the main thread.
        '''
        self._force_stop.set()

    def run(self):
        while (not self.segment_queue.empty()) and\
              (not self._force_stop.is_set()):
            with queue_lock:
                seg_id, seg_url = self.segment_queue.get()
            local_path = f"{self.movie_id}/{seg_id:06d}.ts"
            try:
                utils_http.download_single_segment(seg_url, local_path)
                logging.debug("Downloaded segment %d", seg_id)
                conn = sqlite_conn.SqliteConn()
                conn.update_segment_status(self.movie_id, seg_id, "finished", local_path)
                conn.close()
                # finished_queue.put(seg_id)
            except Exception as e:
                logging.error("Error downloading segment %d: %s", seg_id, str(e))
                with queue_lock:
                    self.segment_queue.put((seg_id, seg_url))
            # download_movie_segment(self.segment_queue, self.movie_id)
            logging.debug("Thread %s finished for movie ID %s", self.name, self.movie_id)

def download_movie_by_segments(movie_to_download: movie.Movie, num_threads: int=config.THREADS):
    """
    Download movie by its segments using multi-threading.
    1. Get all pending segments from database
    2. Create a queue and insert all pending segments into the queue
    3. Create multiple threads to download segments from the queue
    4. Wait for all threads to finish
    """
    # 获取下载文件列表
    conn = sqlite_conn.SqliteConn()
    waiting_segments = conn.get_segments_by_status(movie_to_download.movie_id, 'waiting')
    total_segments_cnt = len(conn.get_segments_by_status(movie_to_download.movie_id))
    conn.close()
    # 创建下载任务队列
    segment_queue = queue.Queue()
    for seg_id, seg_url, _ in waiting_segments:
        segment_queue.put((seg_id, seg_url))
    logging.info("Inserted %i pending tasks into queue", segment_queue.qsize())
    if not os.path.exists(movie_to_download.movie_id):
        os.makedirs(movie_to_download.movie_id)
    logging.info("Creating downloading threads")
    initial_tasks = segment_queue.qsize()
    download_bar = tqdm.tqdm(total=total_segments_cnt,
                             desc=f"Downloading {movie_to_download.movie_id}")
    download_bar.update(total_segments_cnt - initial_tasks)
    task_progress = 0
    # 创建下载线程
    threads = []
    try:
        for i in range(num_threads):
            thread = SegmentDownloadThread(thread_name=f"Thread-{i+1}",
                                       segment_queue=segment_queue,
                                       movie_id=movie_to_download.movie_id)
            thread.start()
            threads.append(thread)
        logging.info("Created %d downloading threads", num_threads)
        while not segment_queue.empty():
            time.sleep(1.0)
            remained_size = segment_queue.qsize()
            download_bar.update(initial_tasks - remained_size - task_progress)
            task_progress = initial_tasks - remained_size
        # 等待所有线程完成
        for thread in threads:
            thread.join()
    except KeyboardInterrupt as e:
        logging.info("Keyboard interrupt detected, stopping all threads")
        for thread in threads:
            thread.stop()
            logging.info("Stopped thread %s. Please wait to finish.", thread.name)
        for thread in threads:
            thread.join()
        raise KeyboardInterrupt("Forced stopping download tasks.") from e
    download_bar.close()
    logging.info("All segments downloaded for movie ID %s", movie_to_download.movie_id)

def merge_ts_into_one(movie_to_download: movie.Movie):
    """
    After finishing all the segments download tasks, merge downloaded *.ts 
    segments into one single title.ts file.
    """
    logging.info("Merging downloaded ts files ...")
    movie_id = movie_to_download.movie_id
    movie_title = movie_to_download.movie_title
    # 合并所有视频片段并重命名
    # os.system(f'copy /b {movie_id}\\*.ts "{movie_title}.ts"')
    with open(f"{movie_title}.ts", 'wb') as fout:
        segment_files = sorted(os.listdir(movie_id))
        merge_bar = tqdm.tqdm(total=len(segment_files), desc=f"Merging {movie_id}")
        for segment_file in segment_files:
            segment_path = os.path.join(movie_id, segment_file)
            with open(segment_path, 'rb') as fin:
                fout.write(fin.read())
            merge_bar.update(1)
        merge_bar.close()
    # 删除下载中间文件
    # os.system(f"rmdir /s /q  {movie_id}")
    shutil.rmtree(movie_id)
    logging.info("Merged all .ts segments into %s.ts", movie_title)

def download_movie(movie_id: str):
    """
    Download a single movie by its movie ID. Firstly check its status, 
    if it is waiting then create tasks and change its status to downloading.
    """
    logging.info("Start downloading movie %s.", movie_id)
    movie_to_download = movie.Movie(movie_id=movie_id, source="database")
    movie_to_download.print()
    if movie_to_download.status == "finished":
        logging.warning("Movie download already finished. Skip downloading.")
        logging.warning("Please reset status=waiting if you want to download again.")
        return
    if movie_to_download.status == "waiting":
        create_movie_segment_tasks(movie_to_download=movie_to_download)
        movie_to_download.change_status("downloading")
    download_movie_by_segments(movie_to_download=movie_to_download)
    merge_ts_into_one(movie_to_download=movie_to_download)
    # After finishing download, delete the segment table
    conn = sqlite_conn.SqliteConn()
    conn.delete_movie_seg_table(movie_id=movie_to_download.movie_id)
    conn.close()
    # 修改电影状态为finished
    movie_to_download.change_status("finished")
    logging.warning("Movie ID %s download finished.", movie_id)

def download_movies_pending():
    """
    Download all pending movies in a batch."""
    movie_pending = get_movie_id_to_download()
    while movie_pending:
        download_movie(movie_pending)
        movie_pending = get_movie_id_to_download()

if __name__ == "__main__":
    download_movies_pending()
    # movie_id = 'sone-123'
    # movie_to_download = movie.Movie(movie_id=movie_id, source="database")
    # merge_ts_into_one(movie_to_download)
