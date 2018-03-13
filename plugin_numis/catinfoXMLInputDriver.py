#!/usr/bin/env python
# -*- coding: utf-8 -*-
# (c) 2014 University of La Rochelle, L3i -- joseph.chazalon@univ-lr.fr

"""
InputDriver child class for cat_info.xml files.
"""

# Sample file except:
# <?xml version="1.0" encoding="utf-8"?>
# <coins>
#     <coin>
#         <image face="avert" x="817" y="180" w="256" h="254" id="9"/>
#         <image face="revert" x="1113" y="175" w="255" h="255" id="6"/>
#         <label x="1071" y="408" w="43" h="25" id="1"/>
#     </coin>
#     ...
# </coins>

# ==============================================================================
# Imports
import logging
import os.path
import xml.sax

import Polygon
import Polygon.Utils

# ==============================================================================
# Project imports
from drivers.InputDriver import UnsupportedFile, SegmentationAnnotation, InputDriver, SelfIntersectingPolygonError
from utils.log import createAndInitLogger
from utils.polygon import isSelfIntersecting

# ==============================================================================
# Logger configuration
logger = createAndInitLogger(__name__) #, debug=True)


# ==============================================================================
known_tags =  tag_coins, tag_coin, tag_image, tag_label = ['coins', 'coin', 'image', 'label']

# ==============================================================================

class XMLFileError(Exception):
    pass


class _catinfoContentHandler(xml.sax.ContentHandler):
    def __init__(self):
        xml.sax.ContentHandler.__init__(self)
        self.eltStack = []
        self.annotations = []
        self.cType = None
        self.cShape = None
        self.cAttrib = None
        self.cAutoId = 0
        self.insideUnk = None # None = No, int = unknown level

    def _parseShapeAttr(self, attrs):
        x = float(attrs.getValue('x'))
        y = float(attrs.getValue('y'))
        w = float(attrs.getValue('w'))
        h = float(attrs.getValue('h'))
        shape = Polygon.Polygon([(x,y), (x,y+h), (x+w,y+h), (x+w, y)])
        if isSelfIntersecting(shape):
            raise BadPolygon(shape)
        self.cShape = shape

    @staticmethod
    def _parseCoinSide(attrs):
        face = attrs.getValue("face")
        f = face[0:min(3,len(face))]
        if f == 'aver':
            return "avers"
        elif f == 'reve':
            return "revers"
        else:
            return "isolated"

    def _autoIdStr(self):
        return "_autogen_%04d" % self.cAutoId

    def _commitAnnot(self):
        self.annotations.append(SegmentationAnnotation(self.cShape, self.cType, self.cAttrib))
        self.cShape = self.cType = self.cAttrib = None

    def startElement(self, name, attrs):
        logger.debug("startElement '" + name + "'")
        self.eltStack.append(name)

        # Actual parsing of known tags
        if name == tag_coins:
            logger.debug("Beginning parsing document.")
        elif name == tag_coin:
            self.cAutoId += 1
        elif name == tag_label:
            self.cType = 'label'
            self._parseShapeAttr(attrs) # TODO try and logger.error + ignore (with insideUnk) if BadPoly?
            self.cAttrib = {'id' : self._autoIdStr()}
        elif name == tag_image:
            self.cType = 'coin'
            self._parseShapeAttr(attrs) # TODO try and logger.error + ignore (with insideUnk) if BadPoly?
            self.cAttrib = {'id' : self._autoIdStr(),
                            'side' : _catinfoContentHandler._parseCoinSide(attrs)}
        else:
            logger.debug("Got unknown opening tag '%s'. Will ignore its content." % name)
            self.insideUnk = len(self.eltStack)

    def endElement(self, name):
        logger.debug("endElement '" + name + "'")
        prevElt = None
        if len(self.eltStack) > 0:
            prevElt = self.eltStack.pop()
        else:
            msg = "Got unexpected element end: '%s'. Expected start of document." % name
            logger.error(msg)
            raise XMLFileError(msg)

        if name != prevElt:
            msg = "Got unexpected element end: '%s'. Expected closing '%s'." % (name, prevElt)
            logger.error(msg)
            raise XMLFileError(msg)

        # Actual parsing of known tags
        if name == tag_coins:
            logger.debug("Finished parsing document.")
        elif name == tag_coin:
            logger.debug("Finished parsing coin info.")
            # pass
        elif name == tag_label:
            logger.debug("Finished parsing label info: shape=%s" % self.cShape)
            self._commitAnnot()
        elif name == tag_image:
            logger.debug("Finished parsing coin side info: shape=%s; side=%s" % (self.cShape, self.cAttrib['side']))
            self._commitAnnot()
        else:
            logger.debug("Got unknown closing tag '%s'." % name)
            
        if self.insideUnk is not None and len(self.eltStack) < self.insideUnk:
            logger.debug("Finished ignoring content of unknown tag '%s'." % name)
            self.insideUnk = None

    def characters(self, content):
        logger.debug("Ignoring text content: %d character(s) skipped." % len(content))


class catinfoXMLInputDriver(object):
    suffix = '.xml'

    @staticmethod
    def load(filename):
        if not catinfoXMLInputDriver.isXMLFile(filename):
            raise UnsupportedFile(filename)

        annotations = None
        try:
            with open(filename, 'rb') as f:
                contenthandler = _catinfoContentHandler()
                xml.sax.parse(f, contenthandler)
                annotations = contenthandler.annotations
        except Exception, e:
            raise XMLFileError(e)

        return annotations


    @staticmethod
    def isXMLFile(filename):
        return os.path.splitext(filename)[1].lower() == catinfoXMLInputDriver.suffix

