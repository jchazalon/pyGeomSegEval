#!/usr/bin/env python
# -*- coding: utf-8 -*-
# (c) 2014 University of La Rochelle, L3i -- joseph.chazalon@univ-lr.fr

"""
Definition of types and basic tools used to read input files.
Actuel reading will depend on the kind of problem considered, and concrete 
classes implementing the InputDriver interface must be provided with
plugins.
"""

# ==============================================================================
# Imports
import logging
from collections import namedtuple

# import Polygon
# import Polygon.Utils

# ==============================================================================
# Project imports
from utils.log import createAndInitLogger

# ==============================================================================
# Logger configuration
logger = createAndInitLogger(__name__)


# ==============================================================================
class UnsupportedFile(Exception):
    """
    Indicates that the file which is being read by the InputDriver instance 
    is not supported. 
    However, it may be readable by another InputDriver child.
    """
    def __init__(self, filename):
        super(UnsupportedFile, self).__init__("File '%s' is of an unsupported format." % filename)


class NoInputDriverCompatibleError(Exception):
    """
    Indicates that no InputDriver child, among those tested, could handle a given file.
    """
    def __init__(self, filename):
        super(NoInputDriverCompatibleError, self).__init__("File '%s' could not be read by any of the InputDriver child provided." % filename)


class SelfIntersectingPolygonError(Exception):
    def __init__(self, polygon):
        super(BadPolygon, self).__init__("Polygon is self-intersecting, and this is not supported.")



def loadWithAnyDriver(filename, input_drivers):
    """
    Try to load an input file with any of the InputDriver child classes provided.
    Classes are tested sequentially and only the first compatible one is used.

    @raise NoInputDriverCompatibleError if no InputDriver is compatible.
    """
    input_data = None
    for driver_cls in input_drivers:
        try:
            logger.debug("Trying to open and load '%s' with driver '%s'." % (filename, driver_cls))
            driver = driver_cls()
            input_data = driver.load(filename)
            break;
        except UnsupportedFile:
            logger.debug("Cannot read '%s' with driver '%s'." %(filename, driver))
            logger.debug("\t Trying next driver, if available...")
    if input_data is None:
        raise NoInputDriverCompatibleError(filename)
    return input_data


    """
    Shape (image surface) + Data (type + attributes with values) = segmentation annotation.

    The shape is described by a polygon, which is formed by a single, non self-intersecting, contour.
    (This may change in the future.)

    Data associated is described (for now) using a very simple structure containing:
    - a type indicator (string) ;
    - a set of (attribute -> value) elements (= dict).

    """
SegmentationAnnotation = namedtuple("SegmentationAnnotation", ["shape", "type", "attributes"])



class InputDriver(object):
    """
    Interface for classes managing input files.
    """

    @staticmethod
    def load(filename):
        """
        Load a file indicated by `filename` and return a sequence of segmentation annotations.

        Childs' implementation must raise `UnsupportedFile` here if the file is
        not supported.

        @return Instance of Sequence<SegmentationAnnotation>

        @raise UnsupportedFile If file is not supported.
        """
        raise NotImplementedError()


