'''__init__ for importing modules for feedtopocket'''

__all__ = ['main']

from  .main import pocketloop, substackloop

def main():
    '''Call pocketloop and substackloop from kobo'''
    pocketloop()
    substackloop()
