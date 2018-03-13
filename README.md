Tool to compare two sets of geometrical segmentations (ground truth and program output, two program outputs, etc.) and compute quality metrics. The target application is document image segmentation evaluation, analysis and improvement.



The core algorithm is based on this paper:

Shafait, F., Keysers, D., & Breuel, T. M. (2008). Performance evaluation and benchmarking of six-page segmentation algorithms. Pattern Analysis and Machine Intelligence, IEEE Transactions on, 30(6), 941-954.

and also on the adaptation proposed here:

Say, V., Coustaty, M., Chazalon, J., Burie, J.-C., & Ogier, J.-M. "Segmentation System and its Evaluation for Gray Scale Coin Documents". In Proceeding of the 4th International Conference on Image Processing Theory, Tools and Applications (IPTA), 2014, Paris, France.

Additional inspiration comes from PrimaResearch tools, hOCR tools, UNLV ISRI tools and many others.



Regarding data processed, each file must contain a set of couples {region, annotation}.
A region is a surface described by a polygon (only representation available now).
An annotation is an type indicator, and a value (not used for now).



Usage:
    eval_geom.py path/to/referenceoutput path/to/testoutput -o optional/output.csv




Ideas:
- experiment optimize linking with a MSER- or connected filter- like selection of matchings based on stable links over all thresholds
- handle multiple types to detect confusions



Extra tool:
- segmenter.py: extracts images parts from images and associated segmentation files


TODO
- add a tool to check GT for manual errors (load all files and collect exceptions)
