'''
Created on Aug 4, 2014

@author: David Zwicker <dzwicker@seas.harvard.edu>
'''

from __future__ import division

import operator

import numpy as np
from scipy import ndimage
from shapely import geometry, geos

import curves
from lib import simplify_polygon_visvalingam as simple_poly 

def corners_to_rect(p1, p2):
    """ creates a rectangle from two corner points.
    The points are both included in the rectangle.
    """
    xmin, xmax = min(p1[0], p2[0]), max(p1[0], p2[0]) 
    ymin, ymax = min(p1[1], p2[1]), max(p1[1], p2[1])
    return (xmin, ymin, xmax - xmin + 1, ymax - ymin + 1)


def rect_to_corners(rect, count=2):
    """ returns `count` corner points for a rectangle.
    These points are included in the rectangle.
    count determines the number of corners. 2 and 4 are allowed values.
    """
    p1 = (rect[0], rect[1])
    p2 = (rect[0] + rect[2] - 1, rect[1] + rect[3] - 1)
    if count == 2:
        return p1, p2
    elif count == 4:
        return p1, (p2[0], p1[1]), p2, (p1[0], p2[1])
    else:
        raise ValueError('count must be 2 or 4 (cannot be %d)' % count)


def rect_to_slices(rect):
    """ creates slices for an array from a rectangle """
    slice_x = slice(rect[0], rect[2] + rect[0])
    slice_y = slice(rect[1], rect[3] + rect[1])
    return slice_y, slice_x


def get_overlapping_slices(t_pos, t_shape, i_shape, anchor='center', ret_rect=False):
    """ calculates slices to compare parts of two images with each other
    i_shape is the shape of the larger image in which a smaller image of
    shape t_shape will be placed.
    Here, t_pos specifies the position of the smaller image in the large one.
    The input variables follow this convention:
        t_pos = (x-position, y-position)
        t_shape = (template-height, template-width)
        i_shape = (image-height, image-width)
    """
    
    # get dimensions to determine center position         
    t_top  = t_shape[0]//2
    t_left = t_shape[1]//2
    if anchor == 'center':
        pos = (t_pos[0] - t_left, t_pos[1] - t_top)
    elif anchor == 'upper left':
        pos = t_pos
    else:
        raise ValueError('Unknown anchor point: %s' % anchor)

    # get the dimensions of the overlapping region        
    h = min(t_shape[0], i_shape[0] - pos[1])
    w = min(t_shape[1], i_shape[1] - pos[0])
    if h <= 0 or w <= 0:
        raise RuntimeError('Template and image do not overlap')
    
    # get the leftmost point in both images
    if pos[0] >= 0:
        i_x, t_x = pos[0], 0
    elif pos[0] <= -t_shape[1]:
        raise RuntimeError('Template and image do not overlap')
    else: # pos[0] < 0:
        i_x, t_x = 0, -pos[0]
        w += pos[0]
        
    # get the upper point in both images
    if pos[1] >= 0:
        i_y, t_y = pos[1], 0
    elif pos[1] <= -t_shape[0]:
        raise RuntimeError('Template and image do not overlap')
    else: # pos[1] < 0:
        i_y, t_y = 0, -pos[1]
        h += pos[1]
        
    # build the slices used to extract the information
    slices= ((slice(t_y, t_y + h), slice(t_x, t_x + w)),  # slice for the template
             (slice(i_y, i_y + h), slice(i_x, i_x + w)))  # slice for the image
    
    if ret_rect:
        return slices, (i_x, i_y, w, h)
    else:
        return slices


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

       
def expand_rectangle(rect, amount=1):
    """ expands a rectangle by a given amount """
    return (rect[0] - amount, rect[1] - amount, rect[2] + 2*amount, rect[3] + 2*amount)
    
       
def get_largest_region(mask, ret_area=False):
    """ returns a mask only containing the largest region """
    # find all regions and label them
    labels, num_features = ndimage.measurements.label(mask)

    # find the label of the largest region
    label_max = np.argmax(
        ndimage.measurements.sum(labels, labels, index=range(1, num_features + 1))
    ) + 1
    
    return labels == label_max


def get_enclosing_outline(polygon):
    """ gets the enclosing outline of a (possibly complex) polygon """
    # get the outline
    outline = polygon.boundary
    
    if isinstance(outline, geometry.multilinestring.MultiLineString):
        largest_polygon = None
        # find the largest polygon, which should be the enclosing outline
        for line in outline:
            poly = geometry.Polygon(line)
            if largest_polygon is None or poly.area > largest_polygon.area:
                largest_polygon = poly
        outline = largest_polygon.boundary
    return outline
    
    
def regularize_polygon(polygon):
    """ regularize a shapely polygon using polygon.buffer(0) """
    # regularize polygon
    result = polygon.buffer(0)
    if isinstance(result, geometry.MultiPolygon):
        # retrieve the result with the largest area
        result = max(result, key=operator.attrgetter('area'))
    return result


def regularize_linear_ring(linear_ring):
    """ regularize a list of points defining a contour """
    polygon = geometry.Polygon(linear_ring)
    regular_polygon = regularize_polygon(polygon)
    if regular_polygon.is_empty:
        return geometry.LinearRing() #< empty ring
    else:
        return regular_polygon.exterior


def regularize_contour_points(contour):
    """ regularize a list of points defining a contour """
    if len(contour) >= 3:
        polygon = geometry.Polygon(np.asarray(contour, np.double))
        regular_polygon = regularize_polygon(polygon)
        if regular_polygon.is_empty:
            return [] #< empty polygon
        else:
            contour = regular_polygon.exterior.coords
    return contour


def simplify_contour(contour, threshold):
    """ simplifies a contour based on its area.
    Single points are removed if the area change of the resulting polygon
    is smaller than `threshold`. 
    """
    if isinstance(contour, geometry.LineString):
        return simple_poly.simplify_line(contour, threshold)
    elif isinstance(contour, geometry.LinearRing):
        return simple_poly.simplify_ring(contour, threshold)
    elif isinstance(contour, geometry.Polygon):
        return simple_poly.simplify_polygon(contour, threshold)
    else:
        # assume contour are coordinates of a linear ring
        ring = geometry.LinearRing(contour)
        ring = simple_poly.simplify_ring(ring, threshold)
        return None if ring is None else ring.coords[:-1]


def get_intersections(geometry1, geometry2):
    """ get intersection points between two (line) geometries """
    # find the intersections between the ray and the burrow outline
    try:
        inter = geometry1.intersection(geometry2)
    except geos.TopologicalError:
        return []
    
    # process the result
    if inter is None or inter.is_empty:
        return []    
    elif isinstance(inter, geometry.Point):
        # intersection is a single point
        return [inter.coords[0]]
    elif isinstance(inter, geometry.MultiPoint):
        # intersection contains multiple points
        return [p.coords[0] for p in inter]
    else:
        # intersection contains objects of lines
        # => we cannot do anything sensible and thus return nothing
        return []

    
def get_ray_hitpoint(point_anchor, point_far, line_string, ret_dist=False):
    """ returns the point where a ray anchored at point_anchor hits the polygon
    given by line_string. The ray extends out to point_far, which should be a
    point beyond the polygon.
    If ret_dist is True, the distance to the hit point is also returned.
    """
    # define the ray
    ray = geometry.LineString((point_anchor, point_far))
    
    # find the intersections between the ray and the burrow outline
    try:
        inter = line_string.intersection(ray)
    except geos.TopologicalError:
        inter = None
    
    # process the result    
    if isinstance(inter, geometry.Point):
        if ret_dist:
            # also return the distance
            dist = curves.point_distance(inter.coords[0], point_anchor)
            return inter.coords[0], dist
        else:
            return inter.coords[0]

    elif inter is not None and not inter.is_empty:
        # find closest intersection if there are many points
        dists = [curves.point_distance(p.coords[0], point_anchor) for p in inter]
        k_min = np.argmin(dists)
        if ret_dist:
            return inter[k_min].coords[0], dists[k_min]
        else:
            return inter[k_min].coords[0]
        
    else:
        # return empty result
        if ret_dist:
            return None, np.nan
        else:
            return None
        
    

def get_ray_intersections(point_anchor, angles, polygon, ray_length=1000):
    """ shoots out rays from point_anchor in different angles and determines
    the points where polygon is hit.
    """
    points = []
    for angle in angles:
        point_far = (point_anchor[0] + ray_length*np.cos(angle),
                     point_anchor[1] + ray_length*np.sin(angle))
        point_hit = get_ray_hitpoint(point_anchor, point_far, polygon)
        points.append(point_hit)
    return points


    
def get_farthest_ray_intersection(point_anchor, angles, polygon, ray_length=1000):
    """ shoots out rays from point_anchor in different angles and determines
    the farthest point where polygon is hit.
    Returns the hit point, its distance to point_anchor and the associated
    angle
    """
    point_max, dist_max, angle_max = None, 0, None
    # try some rays distributed around `angle`
    for angle in angles:
        point_far = (point_anchor[0] + ray_length*np.cos(angle),
                     point_anchor[1] + ray_length*np.sin(angle))
        point_hit, dist_hit = get_ray_hitpoint(point_anchor, point_far,
                                               polygon, ret_dist=True)
        if dist_hit > dist_max:
            dist_max = dist_hit
            point_max = point_hit
            angle_max = angle
    return point_max, dist_max, angle_max



def triangle_area(a, b, c):
    """ returns the area of a triangle with sides a, b, c """
    # use Heron's formula
    s = (a + b + c)/2
    radicand = s*(s - a)*(s - b)*(s - c)
    if radicand > 0:
        return np.sqrt(radicand)
    else:
        # sometimes rounding errors produce small negative quantities
        return 0



def distance_fill(data, start_points, end_points=None):
    """
    fills a binary region of the array `data` with new values.
    The values are based on the distance to the start points `start_points`,
    which must lie in the domain.
    If end_points are supplied, the functions stops when any of these
    points is reached
    """
    if end_points is None:
        end_points = set()
    else:
        end_points = set(end_points)
    
    # initialize the shape
    xmax = data.shape[0] - 1
    ymax = data.shape[1] - 1
    stack = set(start_points) #< initialize the set with the start points

    # the outer loop iterates through all possible distances from the start point    
    # the inner loop iterates through all points with a given distance `dist`
    # `stack` is a set of all points with distance `dist`
    # `stack_next` is a set of all points with distance `dist + 1` 
    dist = 1
    while stack:
        dist += 1
        stack_next = set()
        while stack:
            x, y = stack.pop()
            if data[x, y] == 1:
                data[x, y] = dist
                
                # finish if we found an end point
                if (x, y) in end_points:
                    return 
                
                # add all surrounding points to the stack
                if x > 0:
                    stack_next.add((x - 1, y))
                if x < xmax:
                    stack_next.add((x + 1, y))
                if y > 0:
                    stack_next.add((x, y - 1))
                if y < ymax:
                    stack_next.add((x, y + 1))
                    
        stack = stack_next



def shortest_path_in_distance_map(data, end_point):
    """ finds and returns the shortest path in the distance map `data` that
    leads from the given `end_point` to a start point (defined by having the
    shortest distance) """
    
    xmax = data.shape[1] - 1
    ymax = data.shape[0] - 1
    x, y = end_point
    d = int(data[y, x])
    points = []
    while d > 1:
        points.append((x, y))
        d -= 1
        
        # test diagonal steps
        if x > 0 and y > 0 and data[y - 1, x - 1] == d - 1:
            x -= 1
            y -= 1
            d -= 1
        elif x > 0 and y < ymax and data[y + 1, x - 1] == d - 1:
            x -= 1
            y += 1
            d -= 1
        elif x < xmax and y > 0 and data[y - 1, x + 1] == d - 1:
            x += 1
            y -= 1
            d -= 1
        elif x < xmax and y < ymax and data[y + 1, x + 1] == d - 1:
            x += 1
            y += 1
            d -= 1 
        
        # test horizontal and vertical steps
        elif x > 0 and data[y, x - 1] == d:
            x -= 1
        elif x < xmax and data[y, x + 1] == d:
            x += 1
        elif y > 0 and data[y - 1, x] == d:
            y -= 1
        elif y < ymax and data[y + 1, x] == d:
            y += 1
            
        else:
            break
        
    return points


class Rectangle(object):
    """ a class for handling rectangles """
    def __init__(self, x, y, width, height):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        
    @classmethod
    def from_points(cls, p1, p2):
        x1, x2 = min(p1[0], p2[0]), max(p1[0], p2[0])
        y1, y2 = min(p1[1], p2[1]), max(p1[1], p2[1])
        return cls(x1, y1, x2 - x1, y2 - y1)
    
    def copy(self):
        return self.__class__(self.x, self.y, self.width, self.height)
        
    def __repr__(self):
        return ("Rectangle(x=%g, y=%g, width=%g, height=%g)"
                % (self.x, self.y, self.width, self.height))
            
    @property
    def data(self):
        return self.x, self.y, self.width, self.height
    
    @property
    def data_int(self):
        return (int(self.x), int(self.y),
                int(self.width), int(self.height))
    
    @property
    def left(self):
        return self.x
    @left.setter
    def left(self, value):
        self.x = value
    
    @property
    def right(self):
        return self.x + self.width
    @right.setter
    def right(self, value):
        self.width = value - self.x
    
    @property
    def top(self):
        return self.y
    @top.setter
    def top(self, value):
        self.y = value
    
    @property
    def bottom(self):
        return self.y + self.height
    @bottom.setter
    def bottom(self, value):
        self.height = value - self.y        

    def set_corners(self, p1, p2):
        x1, x2 = min(p1[0], p2[0]), max(p1[0], p2[0])
        y1, y2 = min(p1[1], p2[1]), max(p1[1], p2[1])
        self.x = x1
        self.y = y1
        self.width = x2 - x1
        self.height = y2 - y1     
            
    @property
    def corners(self):
        return (self.x, self.y), (self.x + self.width, self.y + self.height)
    @corners.setter
    def corners(self, ps):
        self.set_corners(ps[0], ps[1])
    
    @property
    def outline(self):
        x2, y2 = self.x + self.width, self.y + self.height
        return ((self.x, self.y), (x2, self.y),
                (x2, y2), (self.x, y2))
    
    @property
    def slices(self):
        slice_x = slice(self.x, self.x + self.width + 1)
        slice_y = slice(self.y, self.y + self.height + 1)
        return slice_x, slice_y

    @property
    def p1(self):
        return (self.x, self.y)
    @p1.setter
    def p1(self, p):
        self.set_corners(p, self.p2)
           
    @property
    def p2(self):
        return (self.x + self.width, self.y + self.height)
    @p2.setter
    def p2(self, p):
        self.set_corners(self.p1, p)
        
    def buffer(self, amount):
        self.x -= amount
        self.y -= amount
        self.width += 2*amount
        self.height += 2*amount
    
    @property
    def area(self):
        return self.width * self.height
