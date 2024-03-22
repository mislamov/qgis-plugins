# -*- coding: utf -8 -*-
# Rosreestr-search-qgis-plugin
# Licensed under the terms of GNU GPL 2
# Thanks to Martin Dobias for the 'QGIS Minimalist Plugin Skeleton'

def classFactory(iface):
    from .pkk6search import Pkk6Search
    return Pkk6Search(iface)
