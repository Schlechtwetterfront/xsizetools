#########################################################
#####                 andecore                      #####
#####         code copyright (C) Ande 2012          #####
#####    https://sites.google.com/site/andescp/     #####
#########################################################


def chunks(list_, n):
    '''Yield n-sized chunks from list_.'''
    for i in xrange(0, len(list_), n):
        yield list_[i:i + n]
