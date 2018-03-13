#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
This file contains the entry point for the Geometrical Segmentation Evaluation Tool.

This tool aims at providing qualitative and quantitative analysis of the results 
produced by some document image segmentation and tagging module.

This tool was developed because, to our knowledge, no free and open source 
software was broadly available and usable with modern systems, nor fulfilling 
the 3 core requirements we had:
1 - the software must be very easy to use and be helpful out of the box;
2 - it must provide very basic service (compare target structure and test structure)
    while being extensible rapidly to handle new file formats and data types;
3 - it must be focused on helping to answer practical questions (like "Are all the 
    objects detected?", "Is my system over- / under- segmenting objects?", "Is there 
    some confusion between the label of the recognized elements?" or "Is my system 
    missing some important part of the objects to detect or adding noise to them?")
    while providing values to enable the improvement of some segmentation system.

The current version only provides a very limited set of features:
 - ground-truth and test result matching;
 - selection of regions based on their label;
 - polygon support;
 - detection and under- / over- segmentation metrics.

New features will be progressively added, but we will ensure that our 3 requirements
are respected.
"""

# Possible extensions to implement:
# - multi types (and confusion)
# - detection and segmentation metrics
# - graph edit distance for structure
# => keep focused on practical problems and generalize only on demand

# TODO
# - compute detection precision and recall
# - compute segmentation precision and recall
# - add visualization of results (separate tool?)
# - separate tests
# - test with empty files
# - test under- and over- segmentation cases
# - improve logging / specify what should go to stderr and to stdout

# It would be very interesting to test building link matrix using Zanibbi's method:
# R. Zanibbi, H. Mouchère, and C. Viard-Gaudin, “Evaluating structural pattern recognition for handwritten math via primitive label graphs,” in Document Recognition and Retrieval XX, Burlingame, United States, 2013, p. 865817.
# (graph edit-based method)

# ==============================================================================
# Imports
import logging
import argparse
import sys
import csv
import numpy as np

# ==============================================================================
# Project imports
from utils.args import *
from utils.log import *
from drivers.InputDriver import *

# Temporary imports
import plugin_numis.lifInputDriver
import plugin_numis.catinfoXMLInputDriver
import csv

# ==============================================================================
# Logger configuration
logger = logging.getLogger(__name__)

# ==============================================================================
# Constants

# Program strings
PROG_VERSION = "0.1"
PROG_NAME = "Geometrical Segmentation Evaluation Tool"
PROG_NAME_SHORT = "eval_geom"

# Error codes
E_OK = 0
E_NOFILE = 10


# ==============================================================================
# SHAPE MATCHING FUNCTIONS

# For matrices:
# - row correspond to reference elements
# - columns correspond to test elements
    
def compute_weight_mat(ref_data_vect, test_data_vect):
    weight_mat = np.empty((len(ref_data_vect), len(test_data_vect)), dtype=np.float)
    #calculate weight, p
    for i in range(len(ref_data_vect)):
        for j in range(len(test_data_vect)):
            inter = ref_data_vect[i].shape & test_data_vect[j].shape
            # FIXME check self intersection of every polygon
            weight_mat[i,j] = inter.area() 
    return weight_mat

def compute_ref_margin_vect(weight_mat):
    reflen, _testlen = weight_mat.shape
    ref_margin_vect = np.empty(reflen, dtype=np.float)
    for i in range(reflen):
        ref_margin_vect[i] = weight_mat[i,:].sum()
    return ref_margin_vect

def compute_test_margin_vect(weight_mat) :
    _reflen, testlen = weight_mat.shape
    test_margin_vect = np.empty(testlen, dtype=np.float)
    for j in range(testlen):
        test_margin_vect[j] = weight_mat[:,j].sum()
    return test_margin_vect


# FIXME parameters
thresholdRelative = 0.2
threshold_ref = 0.5
threshold_test = 0.5
def compute_link_mat(weight_mat, ref_margin_vect, test_margin_vect, ref_data_vect, test_data_vect):
    # Check lengths compatibility
    reflen, testlen = weight_mat.shape
    assert reflen == len(ref_margin_vect) == len(ref_data_vect), \
           "Reference vectors have different lenghts: w:%d m:%d d:%d" % (reflen, len(ref_margin_vect), len(ref_data_vect))
    assert testlen == len(test_margin_vect) == len(test_data_vect), \
           "Test vectors have different lenghts: w:%d m:%d d:%d" % (testlen, len(test_margin_vect), len(test_data_vect))

    link_mat = np.empty((len(ref_data_vect), len(test_data_vect)), dtype=np.bool)
    #matching
    for i in range(len(ref_margin_vect)):
        for j in range(len(test_margin_vect)):
            significant = False
            # note: this is not explicit in the papers, but when weight_mat[i,:] != 0 <=> ref_margin_vect[i] != 0
            #       (same for j)
            #       and there is obviously no link when weight_mat[i,j] == 0
            if weight_mat[i,j] > 0:
                if (weight_mat[i,j]/ref_margin_vect[i]) >= thresholdRelative:
                    if (weight_mat[i,j])/(ref_data_vect[i].shape.area()) > threshold_ref:
                        significant = True
                elif (weight_mat[i,j]/test_margin_vect[j]) >= thresholdRelative:
                    if (weight_mat[i,j])/(test_data_vect[j].shape.area()) > threshold_test:
                        significant = True
            link_mat[i,j] = significant
    return link_mat


# ==============================================================================
# ERROR TYPE CLASSIFICATION FUNCTIONS

# TODO is it possible to factorize the functions (and keep them simple)?

def find_total_correct_segmentation(link_mat):
    """
    Detect 1 to 1 matches (actually correct "detections", which could be better evaluated with prec. & rec. later)
    """
    # FIXME algo could be faster: filter for each line 1-to-1 match and retain (col,row) index, then control in 1 pass (iterate over retained col idx)
    reflen, testlen = link_mat.shape
    total_correct_segmentation = 0 
    for i in range(reflen):
        row_match_count = 0
        col_match_count = 0 
        row_match_index = 0
        # find in test elts matching with current ref elt
        for j in range(testlen):
            if link_mat[i,j]:
                row_match_count += 1
                row_match_index = j
        if row_match_count == 1:
            # only 1 matching in test, is it reciprocal?
            # FIXME extra complexity here
            for ii in range(reflen):
                if link_mat[ii][row_match_index]:
                    col_match_count += 1
            if col_match_count == 1:
                total_correct_segmentation += 1
    return total_correct_segmentation

def find_total_over_segmentation(link_mat):
    """ TODO DOC"""
    reflen, testlen = link_mat.shape
    number_significant_refc = 0
    number_refc_at_least_one_edge = 0
    total_over_segmentation = 0 
    
    for i in range(reflen):
        match_flag = 0
        for j in range(testlen):
            if link_mat[i,j]:
                match_flag += 1
        if match_flag > 1:
            number_refc_at_least_one_edge += match_flag
            number_significant_refc += 1
    total_over_segmentation = number_refc_at_least_one_edge - number_significant_refc
    return total_over_segmentation

def find_total_under_segmentation(link_mat):
    """ TODO DOC"""
    reflen, testlen = link_mat.shape
    number_significant_testc = 0
    number_testc_at_least_one_edge = 0
    total_under_segmentation = 0 
    
    for j in range(testlen):
        match_flag = 0
        for i in range(reflen):
            if link_mat[i,j]:
                match_flag += 1
        if match_flag > 1:
            number_testc_at_least_one_edge += match_flag
            number_significant_testc += 1
    total_under_segmentation = number_testc_at_least_one_edge - number_significant_testc
    return total_under_segmentation

# FIXME merge with find_total_over_segmentation: will be simpler to understand the difference
def find_num_over_segmentation_components(link_mat):  
    """ TODO DOC"""
    reflen, testlen = link_mat.shape
    num_over_segmentation_component = 0
    for i in range(reflen):
        match_flag = 0
        for j in range(testlen):
            if link_mat[i,j]:
                match_flag += 1
        if match_flag > 1:
            num_over_segmentation_component += 1
    return num_over_segmentation_component

def find_num_under_segmentation_components(link_mat): 
    """ TODO DOC"""
    reflen, testlen = link_mat.shape
    num_under_segmentation_component = 0
    for j in range(testlen):
        match_flag = 0
        for i in range(reflen):
            if link_mat[i,j]:
                match_flag += 1
        if match_flag > 1:
            num_under_segmentation_component += 1
    return num_under_segmentation_component

def find_num_missed_components(link_mat): 
    """ TODO DOC"""
    reflen, testlen = link_mat.shape
    num_missed_components = 0
    for i in range(reflen):
        match_flag = 0
        for j in range(testlen):
            if link_mat[i,j]:
                match_flag += 1
                break
        if match_flag == 0:
            num_missed_components += 1
    return num_missed_components

def find_num_false_alarm_components(link_mat):    
    """ TODO DOC"""
    reflen, testlen = link_mat.shape
    num_false_alarm_components = 0
    for j in range(testlen):
        match_flag = 0
        for i in range(reflen):
            if link_mat[i,j]:
                match_flag += 1
                break
        if match_flag == 0:
            num_false_alarm_components += 1
    return num_false_alarm_components



# ==============================================================================
# ENTRY POINT
def main():
    # Option parsing
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description='Evaluate geometrical segmentation results produced by some document image segmentation program.', 
        version=PROG_VERSION)

    parser.add_argument('-d', '--debug', 
        action="store_true", 
        help="Activate debug output.")

    parser.add_argument('reference', 
        action=StoreValidFilePath,
        help='Reference segmentation file.')

    parser.add_argument('test', 
        action=StoreValidFilePath,
        help='Test segmentation file to evaluate against reference.')

    parser.add_argument('-t', '--type-restriction',
        action="append",
        help="Restrict evaluation to annotations with this type. " + 
             "This option can be repeated to allow for multiple types. " +
             "If no restriction is specified, all annotations are considered.")

    parser.add_argument('-o', '--output-file',
        help="Optional path to CSV output file.")

    # TODO option to select plugins (multiple) to use
    # now: load everything / hardcoded elements

    # TODO option to select method to use 
    args = parser.parse_args()

    # -----------------------------------------------------------------------------
    # Logger activation
    initLogger(logger, debug=args.debug)
    
    # -----------------------------------------------------------------------------
    # Output log header
    programHeader(logger, PROG_NAME, PROG_VERSION)
    logger.debug(DBGSEP)
    dumpArgs(args, logger)
    logger.debug(DBGSEP)

    # -----------------------------------------------------------------------------
    logger.debug("Starting up")
    
    # Open files and extract segmentation structure
    available_input_drivers = [plugin_numis.lifInputDriver.lifInputDriver, 
                               plugin_numis.catinfoXMLInputDriver.catinfoXMLInputDriver]
    
    ref_input_vect = loadWithAnyDriver(args.reference, available_input_drivers)
    test_input_vect = loadWithAnyDriver(args.test, available_input_drivers)

    # --------------------------------------------------------------------------
    logger.debug("--- Process started. ---")
    # TODO Extract function

    # Filter components based on label if needed
    ref_data_vect  = ref_input_vect
    test_data_vect = test_input_vect
    if args.type_restriction:
        ref_data_vect  = [annot for annot in ref_input_vect  if annot.type in args.type_restriction]
        test_data_vect = [annot for annot in test_input_vect if annot.type in args.type_restriction]
    # Note: `ref_data_vect` and `test_data_vect` can be empty.

    logger.debug("Compute weighting matrix.")
    weight_mat = compute_weight_mat(ref_data_vect, test_data_vect)
    
    logger.debug("Compute marginal values.")
    ref_margin_vect = compute_ref_margin_vect(weight_mat)
    test_margin_vect = compute_test_margin_vect(weight_mat)

    logger.debug("Compute link matrix.")
    link_mat = compute_link_mat(weight_mat, ref_margin_vect, test_margin_vect, ref_data_vect, test_data_vect)

    # print link_mat # DBG

    logger.debug("Compute statistics.")
    # TODO "find(_num)" -> "count"?
    Tc = find_total_correct_segmentation(link_mat)
    To = find_total_over_segmentation(link_mat)
    Tu = find_total_under_segmentation(link_mat)
    Co = find_num_over_segmentation_components(link_mat)
    Cu = find_num_under_segmentation_components(link_mat)
    Cm = find_num_missed_components(link_mat)
    Cf = find_num_false_alarm_components(link_mat)
    # --
    Cr, Ct = link_mat.shape # Total components considered in reference and test

    logger.debug("--- Process complete. ---")
    # --------------------------------------------------------------------------

    # Display statistics
    # TODO Extract function
    logger.info(DBGSEP)
    logger.info("Segmentation results:")
    logger.info(DBGSEP)
    logger.info("Tc (total correct segmentation) = %d" % Tc)
    logger.info("To (total over segmentation)= %d" % To)
    logger.info("Tu (total under segmentation)= %d" % Tu)
    logger.info("Co (over segmentation components)= %d" % Co)
    logger.info("Cu (under segmentation components)= %d" % Cu)
    logger.info("Cm (missed components)= %d" % Cm)
    logger.info("Cf (false alarms components)= %d" % Cf)
    logger.info("----")
    logger.info("Cr (total components count in reference)= %d" % Cr)
    logger.info("Ct (total components count in test)= %d" % Ct)
    logger.info(DBGSEP)

    # Output to file if requested
    # TODO Extract function
    if args.output_file:
        logger.debug("Exporting results to file '%s'." % args.output_file)
        with open(args.output_file, "wb") as ofile:
            csv_writer = csv.writer(ofile, delimiter='\t', quotechar='"', quoting=csv.QUOTE_NONNUMERIC)
            # Output header
            header = ["RefFile", "TestFile", "Tc", "To", "Tu", "Co", "Cu", "Cm", "Cf", "Cr", "Ct"]
            csv_writer.writerow(header)
            res = [args.reference, args.test, Tc, To, Tu, Co, Cu, Cm, Cf, Cr, Ct]
            csv_writer.writerow(res)
        logger.debug("Done exporting results to file.")


    logger.debug("Clean exit.")
    logger.debug(DBGSEP)
    return E_OK
    # --------------------------------------------------------------------------
    # //main()


if __name__ == "__main__":
    sys.exit(main())

