"""
A simplest downloader of MissAV movies.
The user has to manually find: 
1) video URL pattern, and
2) the movie ID
and set the parameters in the script below.
Author: c_pig8828@163.com
"""

import urllib.request
import os
import re
import logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s: %(message)s')
# settings begin
# This url should be manully set by the user.
URL_MAIN="https://surrit.com/8ee02204-300a-4706-b5dc-d107e8686ebb/720p/video%i.jpeg"
FOLDER_NAME="sone-493"
#settings end
logging.info("Building Request Opener")
opener = urllib.request.build_opener()
host = re.findall(r"https?://([^/]+)/", URL_MAIN)[0]
logging.info("Host=%s", host)
opener.addheaders = [('Host', host)]
urllib.request.install_opener(opener)


logging.info("Start downloading")
count=2070
fail_try=0
if not os.path.exists(FOLDER_NAME):
    os.mkdir(FOLDER_NAME)
    logging.info("Create folder: %s", FOLDER_NAME)
while fail_try<=2:
    video_url = URL_MAIN%count # + url_param
    # print(host)
    target_file = FOLDER_NAME+"\\"+'0'*(6-len(str(count)))+str(count)+".ts"
    try:
        urllib.request.urlretrieve(video_url, target_file)
        #urllib.request.urlopen(video_url)
        logging.info("Downloaded %s", target_file)
        count+=1
        fail_try=0
    except urllib.error.HTTPError as e:
        fail_try+=1
        print(repr(e))
        #print("ERROR: download fail! Part "+str(count))

os.system("copy /b %s\\*.ts %s.ts"%(FOLDER_NAME, FOLDER_NAME))
#os.system("cat "+folder_name+"\\*.ts "+folder_name+".ts")
