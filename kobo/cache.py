#!/usr/bin/env python3
'''
Crawl RSS feeds and either send them to Pocket or render simple
html views, create PDFs of those views and upload them to Dropbox.
The PDFs are formatted to read on a Kobo e-reader.
'''

import os
import time
import datetime
import logging
import operator
import functools
import json
# import configparser
from .constants import STRFTIME #pylint: disable=E0401

class Cache():
    '''A class for caching a dictionary object to a json file'''
    cache_template = {
        'links':{},
        'substack_jail':[False, datetime.datetime.now().strftime(STRFTIME)],
        'cookies': {}
        }

    def __init__(self, opts):
        self.logger = logging.getLogger(__name__)
        self.opts = opts
        self.cache_fn = os.path.join(self.opts.cachedir, __name__+'.json')
        self.cache = self.cache_template
        self.loadcache()

    def loadcache(self):
        ''' Load the cache from disk'''
        if self.opts.dryrun:
            self.logger.info("Loading cache in dry-run mode.")
        if os.path.exists(self.cache_fn):
            self.logger.debug("Loading %s from disk.", self.cache_fn)
            self.cache = json.load(open(self.cache_fn,'rt'))
            for _key in Cache.cache_template:
                if _key not in self.cache:
                    self.logger.debug("Adding missing key %s to cache." , _key)
                    self.cache[_key] = Cache.cache_template[_key]
        else:
            self.logger.warning('%s does not exist, not loading cache template', self.cache_fn)
            self.cache = Cache.cache_template
        return self.cache

    def save(self, updated_cache=None):
        '''Save the cache to disk'''
        if updated_cache:
            self.update(updated_cache)
        if self.opts.dryrun:
            self.logger.info("Dry run, not saving cache.")
        else:
            json.dump(self.cache, open(self.cache_fn, 'wt'))
            self.logger.debug("Cache saved to %s" , self.cache_fn)

    def update(self, updated_cache):
        '''Update the internal cache attribute'''
        self.cache = updated_cache

    def has(self, cache_var, *cache_key):
        '''Check if internal cache has a key/var'''
        try:
            if cache_var in self.get(*cache_key):
                return True
        except KeyError:
            self.logger.debug("Didn't find %s in %s", cache_var, cache_key)
        return False

    def haskey(self, *cache_key):
        '''Check if internal cache has a key/var'''
        try:
            self.get(*cache_key)
            return True
        except KeyError:
            self.logger.debug("Didn't find key %s in internal cache", cache_key)
        return False

    def get(self, *cache_key):
        '''Retreive a value from the cache'''
        try:
            # Equivalent to self.cache[cache_key[0]][cache_key[1]][cache_key[...]]
            return functools.reduce(operator.getitem, cache_key, self.cache)
        except KeyError as err:
            raise KeyError('Key not found in inernal cache.') from err
        ## Does the same as below, but maybe faster?
        # _val = self.cache
        # try:
        #     for _key in cache_key:
        #         _val = _val[_key]
        # except KeyError as err:
        #     raise KeyError('Key not found in inernal cache.') from err
        # return _val

    def set(self, cache_var, *cache_key, commit=False):
        '''Set a value in the cache and save it or not'''
        self.logger.debug("Setting new cache for key %s", cache_key)
        _val = None
        try:
            for _key in reversed(cache_key):
                if _val is None:
                    _val = {_key : cache_var}
                else:
                    _val = {_key:_val}
        except KeyError as err:
            raise KeyError('Key not found in inernal cache.') from err

        for i in range(0, len(cache_key[:-1])):
            if cache_key[i] in self.cache:
                _cached = {cache_key[i]:self.cache[cache_key[i]]}
                for _key in cache_key[i+1:]:
                    if _key not in _cached[cache_key[i]]:
                        _cached[cache_key[i]][_key] = _val[cache_key[i]][_key]
                _val = _cached
                self.logger.debug("Key %s found in internal cache while setting.",
                   cache_key[i])

        # if cache_key[0] in self.cache:
        #     _cached = {cache_key[0]:self.cache[cache_key[0]]}
        #     for _key in cache_key[1:]:
        #         if _key not in _cached[cache_key[0]]:
        #             _cached[cache_key[0]][_key] = _val[cache_key[0]][_key]
        #     _val = _cached
        #     self.logger.debug("Key %s found in internal cache while setting %s.",
        #        cache_key[0], cache_var)

        self.logger.debug("Adding val of type %s to %s in cache.",
                str(type(cache_var)), cache_key)
        self.cache[cache_key[0]] = _val[cache_key[0]]
        if commit:
            self.save()

    def append_unique(self, cache_var, *cache_key, commit=False):
        '''Append unique values to a list in the cache'''
        if not self.has(cache_var, cache_key[0]):
            self.append(cache_var, *cache_key, commit = commit)
        else:
            self.logger.debug("Value %s already exists in cache.", cache_var)

    def append(self, cache_var, *cache_key, commit=False):
        '''Append values to a list in the cache'''
        self.logger.debug("Appending {%s:%s}" , str(cache_key), str(cache_var))
        if not self.haskey(*cache_key):
            raise KeyError('Cannot append to key that is not in internal cache.')
        _val = self.get(*cache_key)
        if isinstance(cache_var, type(_val)):
            self.logger.debug('Concatenating like cache vars')
            _val += cache_var
        else:
            try:
                _val.append(cache_var)
            except AttributeError as err:
                self.logger.error('Error trying to append internal cache')
                raise AttributeError from err
        self.set(_val, *cache_key, commit = commit)

    def reset(self, _key):
        '''Reset a key to default.'''
        self.logger.warning('Resetting %s key in cache.', _key)
        time.sleep(5)
        if _key not in Cache.cache_template:
            raise AttributeError("Trying to reset a non-standard key from cache.")
        self.cache[_key] = Cache.cache_template[_key]
        self.save()

    def __dodedupe(self, _list):
        _vals = []
        for _val in _list:
            if _val not in _vals:
                _vals.append(_val)
            else:
                self.logger.info("Deduping %s", _val)
        return _vals

    def dedupe(self):
        '''Dedeuplicate items and clean keys in the cache'''
        #TODO: this only dedupes dicts two-levels deep
        _deduped = 0
        _cache = Cache.cache_template
        for _key in _cache:
            self.logger.debug("Key %s has %s items",
                    _key, len(self.cache[_key]))
            _vals = []
            if isinstance(self.cache[_key], list):
                self.logger.info("Deduping %s", _key)
                _cache[_key] = self.__dodedupe(self.cache[_key])
            elif isinstance(self.cache[_key], dict):
                for _sub_key in self.cache[_key]:
                    self.logger.info("Deduping %s in %s ", _sub_key, _key)
                    _cache[_key][_sub_key] = self.__dodedupe(self.cache[_key][_sub_key])
            else:
                self.logger.debug("Not deduping non-list key %s", _key)
                _cache[_key] = self.cache[_key]

        self.cache = _cache
        self.logger.info("Deduped %s items", _deduped)

    def cleankey(self, keys_to_compare, *cache_key):
        '''Compare the stored stored to a list of keys and remove
        cached keys that are not in the list'''

        cached = self.get(*cache_key)
        if not isinstance(cached, dict):
            raise KeyError("Can only clean dict objects in cache.")
        cleaned = {}
        for _key in keys_to_compare:
            if _key in cached:
                cleaned[_key] = cached[_key]
        self.set(cleaned, *cache_key, commit=True)
