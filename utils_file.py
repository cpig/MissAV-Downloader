import logging
import os
import shutil

def create_movie_dir(movie_id: str):
    """
    Create a directory for the movie if it doesn't exist.
    """
    if not os.path.exists(movie_id):
        os.makedirs(movie_id)
        logging.debug("Created directory for movie %s.", movie_id)

def delete_movie_dir(movie_id: str):
    """
    Delete the directory for the movie if it exists.
    """
    if os.path.exists(movie_id):
        shutil.rmtree(movie_id)
        logging.debug("Deleted directory for movie %s.", movie_id)

def delete_file(file_path: str):
    """
    Delete a file if it exists.
    """
    if os.path.exists(file_path):
        os.remove(file_path)
        logging.debug("Deleted file %s.", file_path)
