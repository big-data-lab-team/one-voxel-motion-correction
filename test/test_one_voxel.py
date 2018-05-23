#!/usr/bin/env python

from unittest import TestCase
import nibabel
import os
import subprocess


class TestOneVoxel(TestCase):

    def run_command_test(self, command):
        process = subprocess.Popen(command, shell=True,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)
        self.assertFalse(process.returncode)
        return process.stdout.read().decode("utf-8")

    def n_voxels_diff(self, image1, image2):

        count = 0

        im1 = nibabel.load(image1)
        im2 = nibabel.load(image2)
        data1 = im1.get_data()
        data2 = im2.get_data()

        shape = im1.header.get_data_shape()
        assert(len(shape) == 4)
        xdim = shape[0]
        ydim = shape[1]
        zdim = shape[2]
        tdim = shape[3]
        for i in range(0, xdim):
            for j in range(0, ydim):
                for k in range(0, zdim):
                    for t in range(0, tdim):
                        if data1[i][j][k][t] != data2[i][j][k][t]:
                            count += 1
                            assert(round(float(data2[i][j][k][t]) /
                                         float(data1[i][j][k][t]), 1) == 1.0)
        return count

    def test_one_voxel(self):
        input_image = ("./test/data/test.nii.gz")
        output_image = "test/output.nii.gz"
        command = "one_voxel --random {} {}".format(input_image, output_image)
        stdout = self.run_command_test(command)
        self.assertTrue(os.path.exists('test/output.nii.gz'))
        ndiff = self.n_voxels_diff(input_image, output_image)
        print("Found {} voxels with differences".format(ndiff))
        count = 0
        for line in stdout.strip().split(os.linesep):
                print(line)
                if int(line) > 50:
                        count += 1
        self.assertTrue(ndiff == count)
        os.remove(output_image)
