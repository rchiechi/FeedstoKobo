'''Handle parsing an rss feed and uploading the links to pocket'''
import sys
import logging
from .util import hashstring, checkurl

try:
    from pocket import Pocket, PocketException
    import feedparser
except ImportError as msg:
    print("Error loading pacakge %s" , str(msg))
    sys.exit()

class DoPocket():
    '''A class for fetching links and sending them to pocket.'''
    def __init__(self, cache, opts, config):
        self.logger = logging.getLogger(__name__)
        self.opts = opts
        self.cache = cache
        self.pocket_instance = Pocket(
            config['USEROPTS']['CONSUMER_KEY'],
            config['USEROPTS']['ACCESS_TOKEN'])

    def savetopocket(self, _f, _link, _title=''):
        '''Save a link to pocket and cache the result.'''
        _title = _title or 'Morty'
        if not self.cache.haskey('links', hashstring(_f)):
            self.cache.set([], 'links', hashstring(_f))
            self.logger.info("Adding new key for %s in links.", _f)
        if self.cache.has(_link, 'links', hashstring(_f)):
            return False
        if not checkurl(_link):
            self.logger.warning("Not saving %s to pocket because it did not load.", _link)
            return False
        if not self.opts.cacheonly:
            self.logger.debug('Saving %s (%s) to Pocket' , _f, _link)
            if not self.opts.dryrun:
                try:
                    _, _ = self.pocket_instance.add(_link, title=_title)
                    self.cache.append_unique(_link, 'links', hashstring(_f))
                    return True
                except PocketException as msg:
                    self.logger.error("Error adding %s to pocket: %s", _link, str(msg))
                except AttributeError:
                    self.logger.error("No pocket instance, not saving.")
        else:
            self.logger.debug('Caching %s (%s) to Pocket' , _title, _link)
            self.cache.append_unique(_link, 'links', hashstring(_f))
            return True
        return False

    def rsstopocket(self, rss_feeds):
        '''Crawl and RSS feed and upload URLs to Pocket'''
        _cached = []
        for _f in rss_feeds:
            feed = feedparser.parse('https://'+_f)
            if feed['bozo'] == 1:
                self.logger.error(feed['bozo_exception'])
                continue
            for item in feed['entries']:
                if 'title' in item:
                    title = item['title']
                else:
                    title = 'No Title'
                _cached.append(
                        self.savetopocket(_f,
                                    item['link'], title)
                                    )
        return _cached
