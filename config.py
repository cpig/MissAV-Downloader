"""Configuration file for MissAV Downloader."""
# Threads number for downloading segments in parallel.
THREADS = 3

# Single file download timeout setting. (seconds)
HTTP_TIMEOUT = 30

HTTP_RETRY_TIMES = 10

HTTP_RETRY_PERIOD = 30

# Host site main URL
MAIN_SITE = "https://www.missav.com/"

# Movie URL pattern, use movie ID to format.
MOVIE_URL_PATTERN = "https://missav.ws/ja/{}"

# Base HTTP headers for requests
BASE_HEADER = {
    'Accept': 'text/html,application/xhtml+xml,application/xml',
    'Accept-Encoding': 'gzip, deflate, br, zstd',
    'Accept-Language': 'ja-JP,ja;q=0.9,zh-CN;q=0.8,zh;q=0.7,en-US;q=0.6,en;q=0.5'
}
BASE_HEADER_POSTMAN = {
    'User-Agent': 'PostmanRuntime/7.47.1',
    'Accept': '*/*',
    'Cache-Control':'no-cache'}

# SQLite database file path
SQLITE_DB_PATH = "missav.db"
