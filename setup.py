'''Setup script for grabbing rss feeds for reading on a Kobo reader.'''
import os
import setuptools

with open("README.md") as fh:
    long_description = fh.read()

setuptools.setup(name='feedstokobo',
      version='0.1',
      description='Put RSS feeds on your Kobo reader.',
      classifiers=[
        'Development Status :: Beta',
        'Intended Audience :: Kobo users',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Topic :: Kobo :: RSS Feeds :: Substack',
      ],
      package_dir={"": "src"},
      packages=setuptools.find_packages(where="src"),
      python_requires=">=3.2",
      keywords='kobo substack rss',
      url='https://github.com/rchiechi/FeedstoKobo',
      author='Ryan C. Chiechi',
      author_email='r.c.chiechi@rug.nl',
      license='MIT',
      install_requires=[
          'selenium>=3.141.0',
          'colorama>=0.4.4',
          'dropbox>=11.1.0',
          'pocket>=0.3.6',
          'python-pushover>=0.4',
          'feedparser>=6.0.2',
          'pdfkit>=0.6.1'
      ],
      include_package_data=True,
      scripts = [
        os.path.join("src", 'feedstokobo')
        ]
      )
