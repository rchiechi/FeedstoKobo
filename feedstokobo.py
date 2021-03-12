#!/usr/bin/env python3
'''A python script to download rss feeds and substacks and them to
   pocket and dropbox by parsing the text and creating PDFs when required.
   The target is Kobo readers, which can fetch content from these sources.
'''
from feedtopocket.main import pocketloop, substackloop
pocketloop()
substackloop()
