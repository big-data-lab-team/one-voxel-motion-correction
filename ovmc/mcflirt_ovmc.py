#!/usr/bin/env python

import subprocess
import argparse
import os
import shutil
import logging
from logging import info
from logging import error


def run_command(command):
        info(command)
        process = subprocess.Popen(command, shell=True,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)
        (stdout, stderr) = process.communicate()
        if stdout.strip() != "":
            print(stdout.decode("utf-8"))
        if stderr.strip() != "":
            print(stderr.decode("utf-8"))
        if process.returncode != 0:
            raise Exception("mcflirt failed (return"
                            " code was {})".format(process.returncode))


def mcflirt(dataset):
    # Run mcflirt
    output_name = dataset.replace('.nii', '').replace('.gz', '') + "_mcflirt"
    result_path = output_name + '.mat'
    if os.path.exists(result_path):
        shutil.rmtree(result_path)  # in case the result was already here
    command = ("mcflirt -in {} -out {} -plots "
               " -spline_final".format(dataset, output_name))
    run_command(command)


def main():
    parser = argparse.ArgumentParser(
               description="Process the dataset (fMRI"
                           " sequence) with mcflirt and converts the result"
                           " to the format used by ovmc.")
    parser.add_argument("dataset")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO,
                        format='INFO:%(asctime)s %(message)s')
    mcflirt(args.dataset)


if __name__ == '__main__':
    main()
