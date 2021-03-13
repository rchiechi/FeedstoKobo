'''Everything we need to make pdfs from urls and upload them to dropbox.'''

import os
import sys
import time
import datetime
import tempfile
# import contextlib
import logging
from .util import checkurl #pylint: disable=E0401

try:
    import dropbox
    import pdfkit
except ImportError as msg:
    print("Error loading pacakge %s" , str(msg))
    sys.exit()

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
        self.logger = logging.getLogger(__name__)
        self.opts = opts
        self.config = config
        self.dbx = dropbox.Dropbox(config['USEROPTS']['DBACCESS'])

    def dbupload(self, fullname, folder, subfolder, name):
        """Upload a file.
        Return the request response, or None in case of error.
        """
        if self.opts.dryrun:
            return None
        self.logger.info("Uploading %s to Dropbox." , name)
        path = '/%s/%s/%s' % (folder, subfolder.replace(os.path.sep, '/'), name)
        while '//' in path:
            path = path.replace('//', '/')
        # mode = (dropbox.files.WriteMode.overwrite
        #         if overwrite
        #         else dropbox.files.WriteMode.add)
        mtime = os.path.getmtime(fullname)
        with open(fullname, 'rb') as _f:
            data = _f.read()
        # with stopwatch('upload %d bytes' % len(data)):
        try:
            res = self.dbx.files_upload(
                data, path, dropbox.files.WriteMode.overwrite,
                client_modified=datetime.datetime(*time.gmtime(mtime)[:6]),
                mute=True)
        except dropbox.exceptions.ApiError as err:
            self.logger.error('*** API error %s', str(err))
            return None
        self.logger.debug('uploaded as %s' , str(res.name.encode('utf8')))
        return res

    def uritopdf(self, uri, pdfopts, fontsize=None):
        '''Convert a url to a pdf file'''
        if self.opts.dryrun:
            self.logger.info("But not really because dry-run.")
            return  None
        if fontsize is not None:
            pdfopts['minimum-font-size'] = fontsize
        self.logger.debug(pdfopts)
        if not checkurl(uri):
            self.logger.warning("Skipping %s because it does not exist.", uri)
            return None
        try:
            self.logger.info("Saving %s to pdf." , uri)
            pdf = pdfkit.from_url(uri, False, options=pdfopts)
        except OSError as msg:
            if not self.opts.cacheonly:
                self.logger.error("Pdfkit error: %s" , str(msg))
            return None
        with tempfile.NamedTemporaryFile(delete=False) as _fh:
            _fh.write(pdf)
            _fn = _fh.name
        if os.path.getsize(_fn) > 5096: # Check here if a real PDF was made
            return _fn
        return None

    def pdftodropbox(self, pdf_uri, pdfopts, font_size):
        '''Upload a PDF file to Dropbox'''
        tmp_fn = self.uritopdf(pdf_uri, pdfopts, font_size)
        if tmp_fn is not None:
            self.logger.debug("Saving pdf of %s to dropbox." , pdf_uri)
            # dbx = dropbox.Dropbox(DBACCESS)
            self.dbupload(tmp_fn, '/',
                self.config['USEROPTS']['DBREMOTEDIR'],
                pdf_uri.split('/')[-1].replace('.html','.pdf')
                )
            os.remove(tmp_fn)
        else:
            self.logger.debug("Not attepting db upload after pdfkit error.")
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
        self.logger.info("Pruning %s to %s days.",
                        path, days)
        to_delete += __getpdfstodelete(result)
        while result.has_more:
            result = self.dbx.files_list_folder_continue(result)
            to_delete += __getpdfstodelete(result)
        for _c in to_delete:
            if self.opts.dryrun:
                self.logger.info("Not deleting %s", _c.name)
                continue
            try:
                self.dbx.files_delete(_c.path_display)
                self.logger.info("Deleted %s", _c.name)
            except dropbox.exceptions.ApiError:
                self.logger.error("Error deleting %s", _c.name)
# @contextlib.contextmanager
# def stopwatch(message):
#     """Context manager to print how long a block of code took."""
#     _t0 = time.time()
#     try:
#         yield
#     finally:
#         _t1 = time.time()
#         logger.debug('Total elapsed time for %s: %.3f' , message, _t1 - _t0)
