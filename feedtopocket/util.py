'''Utility functions'''

import sys
import os
import logging
import tempfile
import urllib
import hashlib
from .constants import HASH #pylint: disable=E0401

logger = logging.getLogger(__name__)

try:
    import pushover
except ImportError as msg:
    logger.error("Error loading pacakge %s" , str(msg))
    sys.exit()

def sendpushover(po_msg, device, img=None):
    '''Send a pushover message with or without an image'''
    if not po_msg:
        logger.warning("Passed empty message to pushover.")
        return
    client = pushover.Client(device=device)
    po_title=os.path.basename(sys.argv[0])
    if img:
        with tempfile.SpooledTemporaryFile() as image:
            image.write(img)
            image.seek(0)
            client.send_message(po_msg,title=po_title,sound='none',html='1',attachment=image)
    else:
        client.send_message(po_msg,title=po_title,sound='none',html='1')
    logger.debug('Sent a pushover message.')

def checkurl(uri):
    '''See if a URL still exists.'''
    req = urllib.request.Request(
            uri,
            data=None,
            headers={
                'User-Agent':
                'Mozilla/5.0 (Macintosh; '\
                +'Intel Mac OS X 10_9_3) '\
                +'AppleWebKit/537.36 (KHTML, like Gecko) '\
                +'Chrome/35.0.1916.47 Safari/537.36'
            }
                )
    try:
        _res = urllib.request.urlopen(req)
        if _res.getcode() == 200:
            valid = True
    except urllib.error.HTTPError:
        return False
    return valid

def parseloginurls(substacks):
    '''Parse substack login urls and make them neat enough
    to add as command line options'''
    _loginurls = []
    for _ss in substacks:
        _domain = _ss['domain']
        for _path in _domain.split('.'):
            if _path != 'www':
                _key = _path
                break
        _loginurls.append( (_domain,_key) )
    return _loginurls

def hashstring(unhashed_string):
    '''Return a string of a hex digest of a string using
    the HASH algorythm.'''
    _hash = hashlib.new(HASH)
    _hash.update(bytes(unhashed_string, encoding='utf-8'))
    return _hash.hexdigest()

def cleancache(cache, config):
    '''Clean the links key in the cache.'''
    logger.info("Cleaning the links key in the cache.")
    keys = []
    for _key in config['RSS FEEDS']:
        logger.debug("Adding %s", _key)
        keys.append(hashstring(_key))
    for _key in config['SUBSTACKS']:
        logger.debug("Adding %s", config['SUBSTACKS'][_key])
        keys.append(hashstring(config['SUBSTACKS'][_key]))
    cache.cleankey(keys, 'links')

def configtodict(config, keys):
    '''Turn a key from a config object into a dict for pdfkit'''
    dictopts = {}
    for _key in keys:
        if config[_key] == 'False':
            continue
        if config[_key] == 'True':
            _val = ''
        else:
            _val = config[_key]
        dictopts[_key] = _val
    return dictopts
