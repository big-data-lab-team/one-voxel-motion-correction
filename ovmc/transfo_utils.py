import numpy
import math
from math import cos, sin

## Conversions between transformation formats
## More available at https://github.com/glatard/one-voxel/blob/master/scripts/transfo_utils.py

def get_tr_vec(transfo_mat):
    tr_vec = numpy.array([transfo_mat.item(0,3), transfo_mat.item(1,3), transfo_mat.item(2,3)])
    return tr_vec

def get_transfo_vector(transfo_mat):
    tx, ty, tz = get_tr_vec(transfo_mat)
    rx, ry, rz = get_euler_angles(transfo_mat)
    return [tx, ty, tz, rx*180.0/math.pi, ry*180.0/math.pi, rz*180.0/math.pi]

def get_euler_angles(transfo_mat):
    # From http://nghiaho.com/?page_id=846
    rx = math.atan2(transfo_mat.item(2,1), transfo_mat.item(2,2))
    ry = math.atan2(-transfo_mat.item(2,0),
                    math.sqrt(transfo_mat.item(2,1)**2 + transfo_mat.item(2,2)**2)
    )
    rz = math.atan2(transfo_mat.item(1,0), transfo_mat.item(0,0))
    return rx, ry, rz

def get_transfo_mat(x):
    tx, ty, tz, rx, ry, rz = x
    rx = rx*math.pi/180
    ry = ry*math.pi/180
    rz = rz*math.pi/180
    x = numpy.matrix([[1, 0, 0],
                      [0, cos(rx), -sin(rx)],
                      [0, sin(rx), cos(rx)]])
    y = numpy.matrix([[cos(ry), 0, sin(ry)],
                      [0, 1, 0],
                      [-sin(ry), 0, cos(ry)]])
    z = numpy.matrix([[cos(rz), -sin(rz), 0],
                      [sin(rz), cos(rz), 0],
                      [0, 0, 1]])
    r = x*y*z
    mat = numpy.matrix([[ r.item(0,0) , r.item(0,1) , r.item(0,2) , tx],
                        [ r.item(1,0) , r.item(1,1) , r.item(1,2) , ty],
                        [ r.item(2,0) , r.item(2,1) , r.item(2,2) , tz],
                        [ 0 , 0 , 0 , 1]])
    return mat


def diff_transfos(transfo1, transfo2):
    return get_transfo_vector(transfo1*transfo2.I)
