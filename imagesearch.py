#!/usr/bin/python3

import PIL
import sys
from PIL import Image
import logging
from StringIO import StringIO

import requests

from googleapiclient.discovery import build
import authinfo

# Maximum content size to fetch - VGA 24 bit + overhead
MAXIMUM_CONTENT_SIZE = int(320*240*3*1.10)
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
    image_data = image_stream.getvalue()
    logging.debug("image data: {}".format(len(image_data)))
    return image_data

service = build("customsearch", "v1",
    developerKey=authinfo.developer_key)

def getTopImage(search_term):
    try:
        res = service.cse().list(
            q=" ".join(search_term),
            searchType = "image",
            cx=authinfo.ctx,
            safe = "medium"
        ).execute()

        if not 'items' in res:
            logging.debug("No result !!\nres is: {}".format(res))
            return None
        else:
            logging.debug("{} items".format(len(res['items'])))
            for item in res['items']:
                logging.debug("link: {}".format(item['link']))
                image_url = item['link']
                if not image_url or not isSmallContent(image_url):
                    logging.debug("Skipping {}".format(item['link'].encode('utf-8')))
                    continue
                logging.debug("Fetching {} from {}".format(item['title'].encode('utf-8'), item['link'].encode('utf-8')))
                image_stream = StringIO(requests.get(image_url, stream=True, allow_redirects=True).content)
                if image_stream:
                    logging.debug("image was fetched")
                    return getImage(image_stream)
    except Exception, e:
        logging.exception("Error getting image")
    logging.debug("No image fetched")
    return None
