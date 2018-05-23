#!/usr/bin/env python

import argparse
import nibabel
import random


def get_randint(dim, margin):
    return random.randint(max(dim/2-margin, 0), min(dim-1, dim/2+margin))


def main():

    parser = argparse.ArgumentParser(description="Changes the intensity of the\
 central voxel in each volume by 1%.")
    parser.add_argument("image_file")
    parser.add_argument("output_file")
    parser.add_argument("--random", action="store_true",
                        help=("Instead of changing the intensity of the"
                              " central voxel, pick one at random in a 30-voxel"
                              " bounding box centered at the image center."))
    args = parser.parse_args()

    # Load image using nibabel
    im = nibabel.load(args.image_file)

    shape = im.header.get_data_shape()
    assert(len(shape) == 4 or len(shape) == 3)

    xdim = shape[0]
    ydim = shape[1]
    zdim = shape[2]
    tdim = 0
    if (len(shape) == 4):
        tdim = shape[3]

    data = im.get_data()

    margin = 15  # half the size of the bounding box to use to pick a voxel
    if tdim != 0:
        for t in range(0, tdim):
            if not args.random:
                x = xdim/2
                y = ydim/2
                z = zdim/2
            else:
                x = get_randint(xdim, margin)
                y = get_randint(ydim, margin)
                z = get_randint(zdim, margin)
                while(data[x][y][z][t]==0):
                    x = get_randint(xdim, margin)
                    y = get_randint(ydim, margin)
                    z = get_randint(zdim, margin)
            print(data[x][y][z][t])  # used in the test
            data[x][y][z][t] = round(data[x][y][z][t]*1.01)
    else:
        if not args.random:
            x = xdim/2
            y = ydim/2
            z = zdim/2
        else:
            x = get_randint(xdim, margin)
            y = get_randint(ydim, margin)
            z = get_randint(zdim, margin)
        data[x][y][z] = round(data[x][y][z]*1.01)

    im.to_filename(args.output_file)


if __name__ == '__main__':
    main()
