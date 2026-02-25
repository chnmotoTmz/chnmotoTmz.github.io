import os
from dotenv import load_dotenv
import logging

logging.basicConfig(level=logging.DEBUG)
load_dotenv('.env.production')

from lib.thumbnail_task import ThumbnailGeneratorTask

import traceback

task = ThumbnailGeneratorTask()
try:
    res = task.execute({'title': 'Test Thumbnail', 'content': 'Test content'})
    with open('test_thumb_res.txt', 'w', encoding='utf-8') as f:
        f.write("Result: " + str(res))
except Exception as e:
    with open('test_thumb_res.txt', 'w', encoding='utf-8') as f:
        f.write("Exception:\n" + traceback.format_exc())
