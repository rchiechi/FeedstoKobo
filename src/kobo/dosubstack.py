#!/usr/bin/env python3
'''
Crawl RSS feeds and either send them to Pocket or render simple
html views, create PDFs of those views and upload them to Dropbox.
The PDFs are formatted to read on a Kobo e-reader.
'''

import sys
import os
import time
import datetime
import logging
import re
from .constants import STRFTIME
from .util import parseloginurls, sendpushover, hashstring
try:
    import feedparser
    from selenium import webdriver
    from selenium.webdriver.firefox.options import Options
    from selenium.common.exceptions import NoSuchElementException
    from selenium.common.exceptions import InvalidCookieDomainException
    from selenium.common.exceptions import WebDriverException
    from selenium.webdriver.common.proxy import Proxy, ProxyType
except ImportError as msg:
    print("Error loading pacakge %s" , str(msg))
    sys.exit()


class DoSubstack():
    '''Parse a substack URL, turn it into a PDF and upload the PDF.'''

    img_width_re = re.compile('max-width: (\d+)px') #pylint: disable=w1401

    def __init__(self, opts, config, cache):
        self.logger = logging.getLogger(__name__)
        self.logins = {}
        self.cache = cache
        self.opts = opts
        self.useropts = config['USEROPTS']
        self.driver = None
        self.ss_status = {'pause': 0,
                          'fetch error': False,
                          'logged in': False}
        if self.opts.loginurls:
            self.addlogins()

    def parse_ss_entry(self, ss_entry):
        '''Parse a substack entry from SUBSTACKS'''
        self.ss_status['logged in'] = bool(ss_entry['domain'] in self.logins)
        self.ss_status['fetch error'] = False
        rss_feed = feedparser.parse('https://%s/feed' % ss_entry['domain'])
        _pdfs  = []

        if rss_feed['bozo'] == 1:
            self.logger.error(rss_feed['bozo_exception'])
        else:
            if self.driver is None:
                self.__setup_driver()
            for rss_item in rss_feed['entries']:
                _pdf_uri = self.__parse_rss_item(ss_entry, rss_item)
                if self.driver is not None:
                    _title = self.driver.title
                else:
                    _title = None
                _pdfs.append( (rss_item['link'], _pdf_uri, _title) )
        return _pdfs

    def addlogins(self):
        '''Add custom login urls, e.g., to bypass CAPTCHA'''
        for _url in self.opts.loginurls:
            _domain = _url.split(';')[0]
            self.logins[_domain] = _url.split(';')[1]
            self.logger.info("Adding custom login for %s" , _domain)
        self.checkforjail(release=True)
        self.__docustomlogins()

    def cleanup(self):
        '''Call this when all feeds are parsed.'''
        self.logger.debug("Cleaning up web driver.")
        if self.driver is not None:
            self.driver.quit()
            time.sleep(3)
            if os.system('pgrep firefox > /dev/null') == 0:
                self.logger.warning("Manually killing firefox.")
                os.system('killall firefox')

    def __docustomlogins(self):
        '''Use custom login urls to set cookies.'''
        if self.driver is None:
            self.__setup_driver()
        cookies = self.cache.get('cookies')
        for domain in self.logins:
            self.driver.delete_all_cookies()
            self.driver.get(self.logins[domain])
            self.logger.info('Logging in to %s with a custom url.' ,
                domain)
            cookies[domain] = self.driver.get_cookies()
        self.cache.set(cookies, 'cookies')

    def checkforjail(self, release=False):
        '''If not logged in check jail status and relesae if it's been a day'''
        if self.ss_status['logged in']:
            return False

        self.logger.debug("Checking jail status")
        _today = datetime.datetime.now()
        ss_jail = self.cache.get('substack_jail')
        self.logger.debug("Got substack_jail from cache: %s" , str(ss_jail))
        if not ss_jail:
            ss_jail = [False, _today.strftime(STRFTIME)]
        if ss_jail[0]:
            _time_diff = _today - datetime.datetime.strptime(
                ss_jail[1], STRFTIME)
            if _time_diff.days > 0 or release:
                self.logger.info("Releasing from substack jail : )")
                ss_jail[0] = False
                sendpushover("Out of substack jail.",
                        self.useropts['PUSHOVERDEVICE'])
        self.cache.set(ss_jail, 'substack_jail')
        return ss_jail[0]

    def __setup_driver(self):
        ''' Set up the webdriver with a proxy'''
        web_opts = Options()
        web_opts.headless = True
        web_prox = Proxy()
        web_prox.proxy_type = ProxyType.MANUAL
        web_prox.http_proxy = self.useropts['HTTPPROXY']
        web_prox.ssl_proxy = self.useropts['HTTPPROXY']
        web_capabilities = webdriver.DesiredCapabilities.FIREFOX
        web_prox.add_to_capabilities(web_capabilities)
        self.driver = webdriver.Firefox(options=web_opts,
            desired_capabilities=web_capabilities)
        self.driver.implicitly_wait(10) # seconds

    def __parse_rss_item(self, ss_entry, rss_item):
        '''Parse and individual rss item from a ss feed item'''

        _cleandomain = parseloginurls([ss_entry])[0][1]
        url_basename = rss_item['link'].split('/')[-1]
        html_fn = _cleandomain+'-'+url_basename+'.html'
        # pdf_uri = self.useropts['BASEURL']+'/'+ss_entry['subdir']+'/'+html_fn
        pdf_uri = self.useropts['HTMLROOT']+'/'+ss_entry['subdir']+'/'+html_fn

        if self.cache.has(pdf_uri, 'links', hashstring(ss_entry['domain'])):
            return None

        if not self.cache.haskey('links', hashstring(ss_entry['domain'])):
            self.logger.info("Adding new key for %s in links.", ss_entry['domain'])
            self.cache.set([], 'links', hashstring(ss_entry['domain']))

        if url_basename == 'comments'\
                or url_basename[0] == '-'\
                or 'open-thread' in url_basename\
                or 'video-' in url_basename:
            self.logger.warning(
                "Skipping %s because it looks like a comment/podcast/video post.",
                rss_item['link'])
            self.cache.append_unique(pdf_uri, 'links', hashstring(ss_entry['domain']))
            return None

        if not self.opts.cacheonly:
            self.logger.debug("Logging in to  %s", rss_item['link'])
            self.__driver_do_login(ss_entry, rss_item)
            self.logger.debug("Fetching in to  %s", rss_item['link'])
            self.__driver_fetch_item(ss_entry, rss_item['link'], html_fn, pdf_uri)
        if not self.ss_status['fetch error']:
            self.logger.info("Adding %s to cache" , pdf_uri)
            self.cache.append_unique(pdf_uri, 'links', hashstring(ss_entry['domain']))
        else:
            self.logger.warning("Fetch error occured, not caching %s", pdf_uri)
            return None

        return pdf_uri

    def __driver_check_paywall(self, ss_entry, rss_item):
        '''See if we're paywalled.'''

        if not self.cache.has(ss_entry['domain'], 'cookies'):
            self.logger.debug("Adding new cookies domain for %s" , ss_entry['domain'])
            _cookies = self.cache.get('cookies')
            _cookies[ss_entry['domain']] = []
            self.cache.set(_cookies, 'cookies')

        paywalled = False

        try:
            self.driver.delete_all_cookies()
            self.driver.get('https://%s' % ss_entry['domain'])
            time.sleep(3)
            _cookies = self.cache.get('cookies')
            for cookie in _cookies[ss_entry['domain']]:
                try:
                    self.driver.add_cookie(cookie)
                    self.logger.debug("Added cookie for %s." , cookie['domain'])
                except InvalidCookieDomainException:
                    self.logger.warning(
                        "Tried to set cookie from %s for domain %s.",
                            cookie['domain'], ss_entry['domain'])
            self.driver.get(rss_item['link'])
            time.sleep(3)
            paywalled = bool('this post is for paying subscribers'
                in self.driver.find_element_by_class_name('paywall').text.lower())
        except NoSuchElementException:
            self.logger.warning("Didn't find a paywall class? (%s)" , ss_entry['domain'])
        except WebDriverException as msg:
            self.logger.error("Error fetching %s (%s)",
                'https://%s' % ss_entry['domain'], str(msg))
            self.ss_status['fetch error'] = True
        return paywalled

    def __driver_do_login(self, ss_entry, rss_item):
        '''Handle logging in to substack.'''
        if self.ss_status['logged in']:
            return
        paywalled = self.__driver_check_paywall(ss_entry, rss_item)
        if not paywalled:
            # self.ss_status['logged in'] = True
            return
        if self.opts.dryrun:
            return
        # if self.checkforjail() and ss_entry['domain'] not in self.logins:
        if self.checkforjail():
            self.logger.info("Stuck in Substack jail : ( [%s]"
                , rss_item['link'])
            self.ss_status['fetch error'] = True
            return

        self.logger.debug("Pausing for %s seconds." , (self.ss_status['pause']*60))
        time.sleep(self.ss_status['pause'] * 60)
        self.ss_status['pause'] += 1

        self.logger.debug('Logging in to %s' , ss_entry['domain'])
        login_uri='https://%s/account/login?email=%s&with_password=1' \
            % (ss_entry['domain'], ss_entry['login'])
        self.driver.get(login_uri)
        time.sleep(3)
        try:
            self.driver.find_element_by_xpath(
                '//input[@name="password"]'
                    ).send_keys(ss_entry['password'])
            self.driver.find_element_by_xpath(
                '//button[@class="button primary "]'
                    ).submit()
        except NoSuchElementException:
            self.logger.warning(
                "Did not find username / password fields in %s",
                ss_entry['domain']
            )
        _timeout = 30
        while 'my account' in self.driver.title.lower():
            time.sleep(1)
            _timeout -= 1
            if _timeout == 0:
                self.logger.warning('There was an error logging in to %s.' ,
                    ss_entry['domain'])
                self.ss_status['fetch error'] = True
                self.cache.set(
                        [True, datetime.datetime.now().strftime(STRFTIME)],
                        'substack_jail')
                sendpushover(
                    'Error logging in to %s.' % ss_entry['domain'],
                    self.useropts['PUSHOVERDEVICE'],
                    self.driver.get_screenshot_as_png())
                return
            self.ss_status['logged in']=True
            return

    def __driver_fetch_item(self, ss_entry, rss_link, html_fn, pdf_uri):
        '''Once we are logged in and out of jail, we can fetch
            the actual substack entry'''

        html_dir = os.path.join(self.useropts['HTMLROOT']
                    ,ss_entry['subdir'])
        if not os.path.exists(html_dir):
            self.logger.info("Creating %s" , html_dir)
            try:
                os.mkdir(html_dir)
            except OSError as msg:
                self.logger.error("Could not create %s: %s" , html_dir, str(msg))
                self.ss_status['fetch error'] = True
                return not self.ss_status['fetch error']

        if self.ss_status['fetch error']:
            self.logger.warning("Not fetching %s after previous error.", ss_entry['domain'])
            return not self.ss_status['fetch error']

        self.driver.get(rss_link)
        _cookies = self.cache.get('cookies')
        _cookies[ss_entry['domain']] = self.driver.get_cookies()
        self.cache.set(_cookies, 'cookies')
        self.logger.debug('Cached %s cookies for %s.',
            len(_cookies[ss_entry['domain']]), ss_entry['domain'])

        try:
            article = self.driver.find_element_by_class_name('markup')
            if not article.text:
                self.logger.error("Empty article %s", rss_link)
                self.ss_status['fetch error'] = True
                return not self.ss_status['fetch error']
            if 'This is an excerpt from today’s subscriber-only post' in article.text:
                self.logger.warning("Skipping %s because it looks like an excerpt.", rss_link)
                self.ss_status['fetch error'] = False
                return not self.ss_status['fetch error']
            head = self.driver.find_element_by_xpath("//head").get_attribute('innerHTML')
        except NoSuchElementException:
            self.logger.error("Missing article element, cannot parse %s." , rss_link)
            sendpushover('No article found in <a href="%s">post</a>.' % rss_link,
                self.useropts['PUSHOVERDEVICE'])
            self.ss_status['fetch error'] = True
            return not self.ss_status['fetch error']

        with open(os.path.join(html_dir, html_fn), 'wt') as _fh:
            self.logger.debug("Writing to %s", html_fn)
            _fh.write('<head>%s</head>' \
                % head.replace(rss_link, pdf_uri))
            _fh.write('<html><body>\n<h1>%s</h1>\n' \
                % self.driver.find_element_by_tag_name('h1').get_attribute('innerHTML'))
            _fh.write('<html><body>%s' \
                % re.sub(DoSubstack.img_width_re,
                         'max-width: 640px',
                         article.get_attribute('innerHTML')) )
            _fh.write('</body></html>')

        self.ss_status['fetch error'] = False
        return not self.ss_status['fetch error']
