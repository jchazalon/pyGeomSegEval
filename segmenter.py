#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tool to extract segmented image parts given an image and segmentation results
or ground truth file.

Invocation example:
$ find  -iname "*.tif" | \
    parallel python ~/ws_python/pyGeomSegEval/segmenter.py -d \
        -t coin \
        "{}" \
        "{.}.lif"  \
        "/data/datasets/NUMIS-seg200a-coins/{.}" \
    2>&1 | tee /data/datasets/NUMIS-seg200a-coins/00-export-$(timestamp).log


"""


# ==============================================================================
# Imports
import logging
import argparse
import sys
import numpy as np
import cv2

# ==============================================================================
# Project imports
from utils.args import *
from utils.log import *
from drivers.InputDriver import *

# Temporary imports
import plugin_numis.lifInputDriver
import plugin_numis.catinfoXMLInputDriver
# import csv
# TODO output driver

# ==============================================================================
# Logger configuration
logger = logging.getLogger(__name__)

# ==============================================================================
# Constants

# Program strings
PROG_VERSION = "0.1"
PROG_NAME = "Ground Truth Images Segmenter"
PROG_NAME_SHORT = "segmenter"

# Error codes
E_OK = 0
E_NOFILE = 10

# ==============================================================================

# TODO extract to some output driver
def gen_filename_base(atype, attributes):
    if atype == 'coin':
        return "c%s%s" % (attributes['side'][0], attributes['id'])
    elif atype == 'label':
        return "l%s" % (attributes['id'])
    elif atype == 'text':
        return "t%s" % (attributes['id'])
    elif atype == 'noise':
        return "n"
    else:
        raise ValueError("Unknown annotation format: t=%s; attr=%s" % (atype, attributes))


# ==============================================================================
# ==============================================================================
# ENTRY POINT
def main():
    # Option parsing
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description='Generate segmented images from base image and ground truth segmentation file. '
                    + 'Each segmented image will be generated in (approximately) the same format as the input, '
                    + 'and will be accompanied by ".msk" file containing mask information.', 
        version=PROG_VERSION)

    parser.add_argument('-d', '--debug', 
        action="store_true", 
        help="Activate debug output.")

    parser.add_argument('base_image', 
        action=StoreValidFilePath,
        help='Base image.')

    parser.add_argument('seg_file', 
        action=StoreValidFilePath,
        help='File containing segmentation information.')

    parser.add_argument('-t', '--type-restriction',
        action="append",
        help="Restrict the output to objects with this type.")

    parser.add_argument('output_dir',
        action=StoreExistingOrCreatableDir,
        help="Path to a directory where segmented images will be exported.")

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
    
    seg = loadWithAnyDriver(args.seg_file, available_input_drivers)

    # --------------------------------------------------------------------------
    logger.debug("--- Process started. ---")

    # Filter components based on label if needed
    if args.type_restriction:
        seg  = [annot for annot in seg  if annot.type in args.type_restriction]
    # Note: `seg` can be empty.

    img = cv2.imread(args.base_image)
    img_format_ext = os.path.splitext(args.base_image)[1]
    if img_format_ext == "":
        logger.warning("Cannot detect input image format, will use PNG format.")
        img_format_ext = ".png"

    annot_idx = 0
    for (shape, atype, attributes) in seg:
        annot_idx += 1
        logger.debug("Processing annotation %03d with type %s" % (annot_idx, atype))

        (xmin, xmax, ymin, ymax) = shape.boundingBox()

        if xmin == xmax or ymin == ymax:
            logger.error("Annotation %03d was skipped because its area is null." % annot_idx)
            logger.error("\t polygon: %s" % (shape))
            continue

        filename_base = "%03d-%s" % (annot_idx, gen_filename_base(atype, attributes))
        seg_img_fn = os.path.join(args.output_dir, "%s%s" % (filename_base, img_format_ext))
        seg_msk_fn = os.path.join(args.output_dir, "%s%s" % (filename_base, ".msk"))

        roi = img[ymin:ymax, xmin:xmax, :] # TODO test if this works with binary and color images

        shape.shift(-xmin, -ymin)

        msk = np.zeros(roi.shape, dtype=np.uint8)
        white = (255,255,255) # FIXME will not work for RGBA or single color images
        # white = (255,) *  roi.shape[-1]
        cv2.fillPoly(msk, map(lambda c: np.array(c, dtype=np.int32), shape), white)
        masked_roi = cv2.bitwise_and(roi, msk)

        # cv2.imshow('masked image', masked_roi)
        # cv2.waitKey(2000)

        cv2.imwrite(seg_img_fn, masked_roi)

        with open(seg_msk_fn, 'w') as msk_file:
            for c in shape:
                msk_file.write(";".join(map(lambda p: "(%0.2f,%0.2f)" % p, c)))



    logger.debug("--- Process complete. ---")
    # --------------------------------------------------------------------------



    logger.debug("Clean exit.")
    logger.debug(DBGSEP)
    return E_OK
    # --------------------------------------------------------------------------
    # //main()


if __name__ == "__main__":
    sys.exit(main())

