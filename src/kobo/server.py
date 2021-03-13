'''Simple http server to serve html content to pkdfkit.'''
import http.server
import socketserver
import logging
import os
import threading


logger = logging.getLogger(__name__)

class HttpdThread(threading.Thread):
    '''
    A simple Thread to run the http server for pdfkit.
    '''
    def __init__(self):
        threading.Thread.__init__(self)
        # self.htmlroot = _htmlroot
        self.httpd = None
        self.name = 'httpd-thread'

    def run(self):
        '''Overide run method to start a server'''
        port = 8424
        with socketserver.TCPServer(("127.0.0.1", port), Handler) as self.httpd:
            for i in range(5):
                try:
                    logger.debug("serving at port %s", port)
                    self.httpd.serve_forever()
                    break
                except OSError:
                    port += i

    def stop(self):
        '''Shutdown the server'''
        if self.httpd is not None:
            logger.debug("Shutting down the server.")
            self.httpd.shutdown()
            self.httpd.server_close()

class Handler(http.server.SimpleHTTPRequestHandler):
    '''Basic handler to serve html files for pkdfkit.'''
    def do_GET(self):
        logger.debug("Processing GET requst from %s for %s",
                self.headers['X-Real-IP'], self.path)
        if os.path.exists(self.path):
            self.send_response(200)
            self.__sendhtml()
        else:
            logger.warning("%s not found", self.path)
            self.send_response(404)
        self.end_headers()

    def __sendhtml(self):
        with open( self.path , 'rb') as html_fh:
            self.wfile.write(html_fh.read())


if __name__ == '__main__':
    print("Running from CLI for testing")
    import colorama as cm
    import time
    import sys
    cm.init(autoreset=True)
    logger = logging.getLogger(__package__)
    logger.setLevel(logging.DEBUG)
    loghandler = logging.StreamHandler()
    loghandler.setFormatter(logging
                .Formatter(cm.Fore.CYAN+'%(levelname)s '
                            +cm.Fore.YELLOW+'%(message)s'
                            +cm.Style.RESET_ALL))
    logger.addHandler(loghandler)

    htmlroot = os.path.join(
        os.path.expanduser('~'), 'Desktop')
    thread = HttpdThread()
    thread.start()
    try:
        while thread.is_alive():
            time.sleep(1)
            print(threading.enumerate()[-1].name)
    except KeyboardInterrupt:
        thread.stop()
        thread.join()
        sys.exit()
