'''
Created on Aug 4, 2014

@author: zwicker
'''

import numpy as np
import scipy.ndimage as ndimage


def corners_to_rect(p1, p2):
    """ creates a rectangle from two corner points.
    The points are both included in the rectangle.
    """
    xmin, xmax = min(p1[0], p2[0]), max(p1[0], p2[0]) 
    ymin, ymax = min(p1[1], p2[1]), max(p1[1], p2[1])
    return (xmin, ymin, xmax - xmin + 1, ymax - ymin + 1)


def rect_to_corners(rect):
    """ returns two corner points for a rectangle.
    Both these points are included in the rectangle.
    """
    p1 = (rect[0], rect[1])
    p2 = (rect[0] + rect[2] - 1, rect[1] + rect[3] - 1)
    return p1, p2


def rect_to_slices(rect):
    """ creates slices for an array from a rectangle """
    slice_x = slice(rect[0], rect[2] + rect[0])
    slice_y = slice(rect[1], rect[3] + rect[1])
    return slice_y, slice_x


def find_bounding_box(mask):
    """ finds the rectangle, which bounds a white region in a mask.
    The rectangle is returned as [left, top, width, height]
    Currently, this function only works reliably for connected regions 
    """

    # find top boundary
    top = 0
    while not np.any(mask[top, :]):
        top += 1
    # top contains the first non-empty row
    
    # find bottom boundary
    bottom = top + 1
    try:
        while np.any(mask[bottom, :]):
            bottom += 1
    except IndexError:
        bottom = mask.shape[0]
    # bottom contains the first empty row

    # find left boundary
    left = 0
    while not np.any(mask[:, left]):
        left += 1
    # left contains the first non-empty column
    
    # find right boundary
    try:
        right = left + 1
        while np.any(mask[:, right]):
            right += 1
    except IndexError:
        right = mask.shape[1]
    # right contains the first empty column
    
    return (left, top, right - left, bottom - top)

       
def get_largest_region(mask):
    """ returns a mask only containing the largest region """
    # find all regions and label them
    labels, num_features = ndimage.measurements.label(mask)

    # find the label of the largest region
    label_max = np.argmax(
        ndimage.measurements.sum(labels, labels, index=range(1, num_features + 1))
    ) + 1
    
    return labels == label_max