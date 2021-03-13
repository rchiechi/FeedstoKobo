'''
Crawl RSS feeds and either send them to Pocket or render simple
html views, create PDFs of those views and upload them to Dropbox.
The PDFs are formatted to read on a Kobo e-reader.
'''

import sys
import os
import time
import logging
import logging.config
from .options import parseopts
from .dosubstack import DoSubstack
from .cache import Cache
from .pocket import DoPocket
from .dropbox import DoDropbox
from .util import cleancache, configtodict

try:
    import colorama as cm
except ImportError as msg:
    print("Error loading pacakge %s" , str(msg))
    sys.exit()

opts, config = parseopts()

if os.isatty(sys.stdin.fileno()):
    # Debug mode.
    CRONMODE=False
else:
    # Cron mode.
    CRONMODE=True

if CRONMODE:
    # CRONMODE is going to write to a log file, so no color
    opts.nocolor = True

if not opts.nocolor:
    cm.init(autoreset=True)

# Set up terminal logging. Set LOG to a file for cronmode, otherwise
# colorful terminal output.
logger = logging.getLogger(__package__)
logger.setLevel(getattr(logging, opts.logging.upper()))
if CRONMODE:
    loghandler = logging.FileHandler(os.path.join(opts.logdir,
                                     os.path.basename(sys.argv[0])
                                     .split('.')[0]+'.txt'))
else:
    loghandler = logging.StreamHandler()
if opts.nocolor:
    loghandler.setFormatter(logging
                .Formatter('%(asctime)s %(process)d %(levelname)s %(message)s'))
else:
    loghandler.setFormatter(logging
                .Formatter(cm.Fore.CYAN+'%(levelname)s '
                            +cm.Fore.YELLOW+'%(message)s'
                            +cm.Style.RESET_ALL))
logger.addHandler(loghandler)

############################################################
# Now we can use the logger                                #
############################################################

if config is None:
    logger.error("No config file found.")
    logger.info("Default file created at %s", opts.configdir)
    sys.exit()

cache = Cache(opts)
if opts.clean:
    cleancache(cache, config)
if opts.reset:
    if not opts.cacheonly:
        logger.warning('Reseting cache without --cacheonly is dangerous.')
        time.sleep(5)
    cache.reset('links')
if opts.dedupe:
    cache.dedupe()
    logger.info("%s links in cache", len(cache.get('links')))

try:
    # For pdfkit?
    os.environ['XDG_RUNTIME_DIR'] = os.path.join('/tmp',
        'runtime-%s' % os.environ['USER'])
except KeyError as msg:
    logger.warning("Couldn't set XDG_RUNTIME_DIR. %s" , str(msg))

# Our three main classes for pocket, dropbox and substack
pocket = DoPocket(cache, opts, config)
dropbox = DoDropbox(opts, config)
substack = DoSubstack(opts, config, cache)

def pocketloop():
    '''Crawl an rss feed and cache the links to pocket.'''

    logger.info("Starting RSS run.")
    p_cached = pocket.rsstopocket(list(config['RSS FEEDS']))
    logger.info("Cached %s urls to pocket.", p_cached.count(True))
    if True in p_cached or opts.cacheonly:
        cache.save()

def substackloop():
    '''Substacks rendered to html on Morty
        send to Pocket rendered to PDFs
        and uploaded to Dropbox'''

    logger.info("Starting Substack run.")
    pdfopts = configtodict(config['PDFOPTIONS'],
        DoDropbox.PDFOPTIONS)
    ss_cached = []
    for _ss in config['SUBSTACKS']:
        _f = {'domain': config['SUBSTACKS'][_ss],
              'fontsize': pdfopts['minimum-font-size'],
              'login': config['USEROPTS']['SSLOGIN'],
              'password': config['USEROPTS']['SSPASS'],
              'subdir': _ss
              }
        if _ss in config.sections():
            for _key in ('fontsize', 'login', 'password'):
                if _key in config[_ss]:
                    _f[_key] = config[_ss][_key]

        pdfs = substack.parse_ss_entry(_f)
        for _uri, _pdf_uri, _title in pdfs:
            if _pdf_uri is not None:
                pocket.savetopocket(_f['domain'], _uri,  _title)
            if not opts.cacheonly and _pdf_uri is not None:
                logger.debug("Attempting to upload %s from %s to dropbox."
                        , _pdf_uri, _f['domain'])
                ss_cached.append(dropbox.pdftodropbox(_pdf_uri,
                            pdfopts, _f['fontsize']))

    logger.info("Cached %s substacks to Dropbox.", ss_cached.count(True))

    if True in ss_cached or opts.cacheonly:
        cache.save()
    if False in ss_cached:
        logger.warning("There were errors uploading PDFs to dropbox.")
    substack.cleanup()

    if opts.prunedropbox:
        dropbox.prunedropbox(opts.prunedropbox)

    logger.info("#### Done ####")
