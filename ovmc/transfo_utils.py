import numpy
import math
from math import cos, sin

## Conversions between transformation formats

def get_rot_angle_vec(rot_mat):
    # See http://www.euclideanspace.com/maths/geometry/rotations/conversions/matrixToAngle/
    cos = (rot_mat.item(0,0)+rot_mat.item(1,1)+rot_mat.item(2,2)-1)/2
    if(cos > 1):
        print("Warning: cos is larger than 1: {0}".format(cos))
        cos = 1
    rot_angle = math.acos(cos)
    x = (rot_mat.item(2,1)-rot_mat.item(1,2))/math.sqrt((rot_mat.item(2,1)-rot_mat.item(1,2))**2+(rot_mat.item(0,2)-rot_mat.item(2,0))**2 + (rot_mat.item(1,0)-rot_mat.item(0,1))**2)
    y = (rot_mat.item(0,2)-rot_mat.item(2,0))/math.sqrt((rot_mat.item(2,1)-rot_mat.item(1,2))**2+(rot_mat.item(0,2)-rot_mat.item(2,0))**2 + (rot_mat.item(1,0)-rot_mat.item(0,1))**2)
    z = (rot_mat.item(1,0)-rot_mat.item(0,1))/math.sqrt((rot_mat.item(2,1)-rot_mat.item(1,2))**2+(rot_mat.item(0,2)-rot_mat.item(2,0))**2 + (rot_mat.item(1,0)-rot_mat.item(0,1))**2)
    rot_vec = numpy.array([x, y, z])
    return rot_angle, rot_vec
   
def get_rot_mat(transfo_mat):
    rot_mat = numpy.matrix([[transfo_mat.item(0,0), transfo_mat.item(0,1), transfo_mat.item(0,2)],
                           [transfo_mat.item(1,0), transfo_mat.item(1,1), transfo_mat.item(1,2)],
                           [transfo_mat.item(2,0), transfo_mat.item(2,1), transfo_mat.item(2,2)]])
    return rot_mat

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

def framewise_displacement(transfo_vec):
    tx, ty, tz, rx, ry, rz = transfo_vec
    rx = rx/180.0*math.pi
    ry = ry/180.0*math.pi
    rz = rz/180.0*math.pi
    fd = (abs(rx) * 50 + abs(ry) * 50 + abs(rz) * 50
          + abs(tx) + abs(ty) + abs(tz))
    return fd
 
# Reads an MNI xfm transformation
def read_transfo(file_name):
    transfo = numpy.zeros(shape=(4, 4))
    transfo_line = -1
    with open(file_name) as f:
        for line in f:
            line = line.strip()
            if transfo_line >= 0 and transfo_line < 3:
                elements = line.split()
                assert(len(elements) == 4), "Wrong format in transformation line: {0} (file name: {1})".format(line, file_name)
                for i in range(0, 4):
                    transfo[transfo_line][i] = float(elements[i].strip().replace(";",""))
                transfo_line += 1
            if transfo_line >= 4:
                break
            if line.startswith("Linear_Transform"):
                transfo_line = 0

    transfo_mat = numpy.matrix([[transfo[0][0], transfo[0][1], transfo[0][2], transfo[0][3]],
        [transfo[1][0], transfo[1][1], transfo[1][2], transfo[1][3]],
        [transfo[2][0], transfo[2][1], transfo[2][2], transfo[2][3]],
        [0, 0, 0, 1]
    ])

    return transfo_mat

# Prints an MNI xfm transformation
def print_mat(x, file_name):
    s = "{0} {1} {2} {3}\n{4} {5} {6} {7}\n{8} {9} {10} {11}\n".format(
        x.item(0,0), x.item(0,1), x.item(0,2), x.item(0,3),
        x.item(1,0), x.item(1,1), x.item(1,2), x.item(1,3),
        x.item(2,0), x.item(2,1), x.item(2,2), x.item(2,3))        
    with open(file_name, 'w') as f:
        f.write("MNI Transform File\n")
        f.write("Transform_Type = Linear;\nLinear_Transform =\n")
        f.write(s)
        f.write(";")

