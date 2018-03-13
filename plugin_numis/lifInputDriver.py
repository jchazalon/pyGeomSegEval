#!/usr/bin/env python
# -*- coding: utf-8 -*-
# (c) 2014 University of La Rochelle, L3i -- joseph.chazalon@univ-lr.fr

"""
InputDriver child class for LIF files.
"""

# ==============================================================================
# Imports
import logging
import json
import os.path

import Polygon
import Polygon.Utils

# ==============================================================================
# Project imports
from drivers.InputDriver import UnsupportedFile, SegmentationAnnotation, InputDriver, SelfIntersectingPolygonError
from utils.log import createAndInitLogger
from utils.polygon import isSelfIntersecting

# ==============================================================================
# Logger configuration
logger = createAndInitLogger(__name__)


# ==============================================================================

class LabelFileError(Exception):
    pass

class lifInputDriver(object):
    suffix = '.lif'

    typemapping = { 'c' : 'coin',
                    'l' : 'label',
                    't' : 'text',
                    'n' : 'noise' }
    coinsidemapping = { 'a' : 'avers',
                        'r' : 'revers',
                        'i' : 'isolated' }

    @staticmethod
    def parseLabel(label):
        """str -> (str x map(str -> value))"""
        # labels: 
        # coin - avers / revers / isolée - id == ca101 cr101 ci101
        # label - id == l101
        # texte - id == t101
        # noise == n
        if len(label) < 1:
            raise ValueError(label)

        atype = None
        attributes = {}

        c0 = label[0]
        if c0 not in lifInputDriver.typemapping:
            raise ValueError(label)

        atype = lifInputDriver.typemapping[c0]

        if atype == 'coin':
            if len(label) < 3:
                raise ValueError(label)

            c1 = label[1]
            if c1 not in lifInputDriver.coinsidemapping:
                raise ValueError(label)

            attributes['side'] = lifInputDriver.coinsidemapping[c1]
            attributes['id']  = label[2:]

        elif atype == 'label':
            if len(label) < 2:
                raise ValueError(label)
            attributes['id']  = label[1:]

        elif atype == 'text':
            if len(label) < 2:
                raise ValueError(label)
            attributes['id']  = label[1:]

        elif atype == 'noise':
            pass

        else:
            raise ValueError(label)

        return (atype, attributes)


    @staticmethod
    def load(filename):
        if not lifInputDriver.isLabelFile(filename):
            raise UnsupportedFile(filename)

        results = []
        try:
            with open(filename, 'rb') as f:
                data = json.load(f)
                for s in data['shapes']:
                    shape = Polygon.Polygon(s['points'])
                    if isSelfIntersecting(shape):
                        raise SelfIntersectingPolygonError(shape)
                    atype, attributes = lifInputDriver.parseLabel(s['label'])
                    results.append(SegmentationAnnotation(shape, atype, attributes))

        except Exception, e:
            raise LabelFileError(e)

        return results


    @staticmethod
    def isLabelFile(filename):
        return os.path.splitext(filename)[1].lower() == lifInputDriver.suffix

