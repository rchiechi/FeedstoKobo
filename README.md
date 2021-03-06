# FeedstoKobo
Parse rss feeds and send them to Pocket, render Substacks to PDFs and send them to Dropbox to read on a Kobo Reader.

I wrote this for myself because I prefer reading long articles on my Kobo e-reader.
**Don't expect anything fancy.**

Pocket cannot render Substacks and Kobo readers can only render pocket entries, not redirects.
But Kobo readers can load PDFs from Dropbox.
FeedstoKobo, therefore, will try to render PDFs from Substack entries.
It seems like the folks at Substack don't want you to do that, so substack will throw up CAPTCHA pages.
It will also lock you out of your account for 24 hours if you fail to log in too many times in a row.
FeedstoKobo will take custom login urls (that Substack sends you by email) and try to authenticate with those, should you have CAPTCHA issues.

# Setup
This script is meant to be called as a cron job on a headless server. It has only been tested on Ubuntu 20.04.2 LTS.

- The server should also have a local proxy that, preferably, resolves to the same IP address you use to read Substack at home.
- It will walk through RSS feeds and save them to pocket. You're on your own for getting your [Pocket OAuth credentials](https://getpocket.com/developer/apps/new).
- It will render Substack entries to PDFs and save them to Dropbox. You're on your own for getting your [Dropbox App credentials](https://www.dropbox.com/developers/reference/getting-started#app%20console).
- It will send you a Pushover with a screenshot if a login fails. Youre on your own for getting your [Pushover API key](https://pushover.net/api).

Selenium will spawn a headless Firefox session and pdfkit uses wkhtmltopdf, so you'll have to have both of those programs installed.
FeedstoKobo will kill all running Firefox sessions at the end of a run, so do not run it on a computer on which you use Firefox for other things.

# Installation 
You can run this script directly from the src directory.
TO do that you will need to install the following packages (via pip3) on your server:
- python-pushover
- dropbox
- pocket
- colorama
- feedparser
- selenium
- pdfkit

Alterantivey you can clone this repo, navigate to the root folder and type `pip3 install .` or `pip3 install --local .`

