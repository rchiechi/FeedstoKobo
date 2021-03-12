'''Parse command line args and config files'''
import os
import argparse
import configparser

def parseopts():
    '''Parse commandline arguments and config file and return opts, config'''

    desc='''Crawl RSS feeds and send then to Pocket
          or convert to a PDF and send them to Dropbox.'''
    parser = argparse.ArgumentParser(description=desc,
                                  formatter_class=argparse
                                  .ArgumentDefaultsHelpFormatter)

    parser.add_argument('-d','--dryrun', action="store_true", default=False,
         help="Dry-run, do not save anything.")

    parser.add_argument('-c','--cacheonly', action="store_true", default=False,
         help="Cache RSS entries instead of uploading them.")

    parser.add_argument('--logdir', action="store",
         default=os.path.join(os.path.expanduser('~'),'logs'),
         help="Set the output dir for the logfile.")

    parser.add_argument('--configdir', action="store",
         default=os.path.join(os.path.expanduser('~'),'.config'),
         help="Set the dir to look for the config file.")

    parser.add_argument('--cachedir', action="store",
        default=os.path.join(os.path.expanduser('~'),'.cache'),
        help="Set the output dir for the cache file.")

    parser.add_argument('-L','--logging', action="store", default="info",
         choices=['debug', 'info', 'warning', 'error', 'critical'],
         help="Set the log level (critical, warning, info).")

    parser.add_argument('--nocolor', action="store_true", default=False,
         help="Turn off colored output (useful when called from another script.")

    parser.add_argument('--dedupe', action="store_true", default=False,
         help="Dedupe the cache.")

    parser.add_argument('--reset', action="store_true", default=False,
       help="Reset the cache.")

    parser.add_argument('--clean', action="store_true", default=False,
       help="Clean the cache, for example, after removing an rss feed.")

    parser.add_argument('--prunedropbox', action="store", type=int,
        choices=[1,2,3,4,5,6,7,8,9,10,11,12,13,14],
       help="Prune dropbox to a number of days between 1-14.")

    parser.add_argument('--loginurls', action="store", nargs='*',
       help="Custom login urls in the form 'domain;url' for substacks, e.g., to bypass CAPTCHA.")
    # for _login in loginurls:
    #     parser.add_argument('--%s' % _login[1] ,
    #                         action="store", metavar='URL',
    #                         help="Add a custom login url for %s." % _login[0])
      # loginurls.append( (_domain,_key) )

    # Read user options
    opts=parser.parse_args()
    config = doconfig(os.path.join(opts.configdir,
          __package__+'.conf')
          )
    # config_file = os.path.join(opts.configdir,
    #       __package__+'.conf')
    # config = configparser.ConfigParser(allow_no_value=True)
    # config.read(os.path.join(opts.configdir,
    #       __package__+'.conf'))

    return opts,config

def doconfig(config_file):
    '''Parse config file or write a default file.'''
    config = configparser.ConfigParser(allow_no_value=True)
    config.read(config_file)
    if 'USEROPTS' not in config:
        config = configparser.ConfigParser(allow_no_value=True)
        config.read(os.path.basename(config_file))
    return config
