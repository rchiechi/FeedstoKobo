'''Everything we need to make pdfs from urls and upload them to dropbox.'''

import os
import sys
import time
import datetime
import tempfile
import logging
from .util import checkurl
from .server import HttpdThread

try:
    import dropbox
    import pdfkit
except ImportError as msg:
    print("Error loading pacakge %s" , str(msg))
    sys.exit()

logger = logging.getLogger(__name__)

class DoDropbox():
    '''Handling making pdfs and uplading them to dropbox.'''

    PDFOPTIONS = {
                'page-height': '155mm',
                'page-width': '115mm',
                'margin-top': '2mm',
                'margin-right': '2mm',
                'margin-bottom': '2mm',
                'margin-left': '2mm',
                'minimum-font-size': '32',
                'encoding': "UTF-8",
                'grayscale': '',
                'quiet': ''
                }

    def __init__(self, opts, config):
        self.opts = opts
        self.config = config
        self.dbx = dropbox.Dropbox(config['USEROPTS']['DBACCESS'])
        self.httpd = None

    def pdftodropbox(self, pdf_uri, pdfopts, font_size):
        '''Upload a PDF file to Dropbox'''
        if self.opts.dryrun:
            logger.info("But not really because dry-run.")
            return  True
        # if self.httpd is None:
        #     self.httpd = HttpdThread()
        #     self.httpd.start()
        tmp_fn = uritopdf(pdf_uri, pdfopts, font_size)
        if tmp_fn is not None:
            logger.debug("Saving pdf of %s to dropbox." , pdf_uri)
            self.__dbupload(tmp_fn, '/',
                self.config['USEROPTS']['DBREMOTEDIR'],
                pdf_uri.split('/')[-1].replace('.html','.pdf')
                )
            os.remove(tmp_fn)
        else:
            logger.debug("Not attepting db upload after pdfkit error.")
            return False
        return True

    def prunedropbox(self, days):
        '''Prune the uploaded PDFs to files younger than days.'''
        path = self.config['USEROPTS']['DBREMOTEDIR']
        while '//' in path:
            path = path.replace('//', '/')
        result = self.dbx.files_list_folder(path)
        _today = datetime.datetime.now()
        to_delete = []
        def __getpdfstodelete(cursor):
            '''Iterate through PDF dir and collect files older
            than a week to delete'''
            _to_delete = []
            for _c in cursor.entries:
                _time_diff = _today - _c.server_modified
                if _time_diff.days >= int(days):
                    _to_delete.append(_c)
            return _to_delete
        logger.info("Pruning %s to %s days.",
                        path, days)
        to_delete += __getpdfstodelete(result)
        while result.has_more:
            result = self.dbx.files_list_folder_continue(result)
            to_delete += __getpdfstodelete(result)
        for _c in to_delete:
            if self.opts.dryrun:
                logger.info("Not deleting %s", _c.name)
                continue
            try:
                self.dbx.files_delete(_c.path_display)
                logger.info("Deleted %s", _c.name)
            except dropbox.exceptions.ApiError:
                logger.error("Error deleting %s", _c.name)

    def cleanup(self):
        '''Clean up after all PDFs are uploaded.'''
        if self.httpd is not None:
            self.httpd.stop()
            self.httpd.join()

    def __dbupload(self, fullname, folder, subfolder, name):
        """Upload a file.
        Return the request response, or None in case of error.
        """
        if self.opts.dryrun:
            return None
        logger.info("Uploading %s to Dropbox." , name)
        path = '/%s/%s/%s' % (folder, subfolder.replace(os.path.sep, '/'), name)
        while '//' in path:
            path = path.replace('//', '/')
        mtime = os.path.getmtime(fullname)
        with open(fullname, 'rb') as _f:
            data = _f.read()
        try:
            res = self.dbx.files_upload(
                data, path, dropbox.files.WriteMode.overwrite,
                client_modified=datetime.datetime(*time.gmtime(mtime)[:6]),
                mute=True)
        except dropbox.exceptions.ApiError as err:
            logger.error('*** API error %s', str(err))
            return None
        logger.debug('uploaded as %s' , str(res.name.encode('utf8')))
        return res


def uritopdf(uri, pdfopts, fontsize=None):
    '''Convert a url to a pdf file'''
    if fontsize is not None:
        pdfopts['minimum-font-size'] = fontsize
    logger.debug(pdfopts)
    if not checkurl(uri):
        logger.warning("Skipping %s because it does not exist.", uri)
        return None
    try:
        logger.info("Saving %s to pdf." , uri)
        # pdf = pdfkit.from_url(uri, False, options=pdfopts)
        pdf = pdfkit.from_file(uri, False, options=pdfopts)
    except OSError:
        return None
    with tempfile.NamedTemporaryFile(delete=False) as _fh:
        _fh.write(pdf)
        _fn = _fh.name
    if os.path.getsize(_fn) > 5096: # Check here if a real PDF was made
        return _fn
    return None
