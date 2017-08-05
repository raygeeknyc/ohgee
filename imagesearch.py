import PIL
from PIL import Image
import logging
from StringIO import StringIO

import requests

from googleapiclient.discovery import build
import authinfo

# Maximum content size to fetch - VGA 24 bit + overhead
MAXIMUM_CONTENT_SIZE = int(640*480*3*1.10)
DISPLAY_RESOLUTION = (640,480)

def isSmallContent(url):
    header = requests.head(url, allow_redirects=True).headers
    content_type = header.get('content-type')
    if 'text' in content_type.lower() or 'html' in content_type.lower():
        logging.debug("content-type: {}".format(content_type))
        return False
    content_length = int(header.get('content-length') or MAXIMUM_CONTENT_SIZE+1)
    if content_length > MAXIMUM_CONTENT_SIZE:
        logging.debug("content-length: {}".format(content_length))
        return False
    return True

def getImage(image_stream):
    image = Image.open(image_stream)
    image = image.resize(DISPLAY_RESOLUTION)
    return image

service = build("customsearch", "v1",
    developerKey=authinfo.developer_key)

def getTopImage(search_term):
    res = service.cse().list(
        q=" ".join(search_term),
        searchType = "image",
        cx=authinfo.ctx
    ).execute()

    if not 'items' in res:
        logging.debug("No result !!\nres is: {}".format(res))
        return None
    else:
        for item in res['items']:
            image_url = item['link']
            if not image_url or not isSmallContent(image_url):
                logging.debug("Skipping {}".format(item['link'].encode('utf-8')))
                continue
            logging.debug("Fetching {} from {}".format(item['title'].encode('utf-8'), item['link'].encode('utf-8')))
            image_stream = StringIO(requests.get(image_url, stream=True, allow_redirects=True).content)
            if image_stream:
                return getImage(image_stream)
    return None
