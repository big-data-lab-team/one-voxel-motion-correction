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


def spm(dataset, output_file_name):
    raise Exception("Not implemented yet!")


def niaklike(dataset, output_file_name, chained_init=True):
    raise Exception("Not implemented yet!")


def niaklike_no_chained_init(dataset, output_file_name):
    niaklike(dataset, output_file_name, False)


def mcflirt_fudge(dataset, output_file_name):
    mcflirt(dataset, output_file_name, True)


def mcflirt(dataset, output_file_name, fudge=False):
    # Run mcflirt
    output_file_name = output_file_name.replace('.par', '')
    if os.path.exists(output_file_name):
        shutil.rmtree(output_file_name)
    command = ("mcflirt -in {} -out {} -plots "
               " -spline_final".format(dataset, output_name))
    if fudge:
        command += " -fudge"
    run_command(command)


def check_file(parser, x):
    if os.path.exists(x):
        return x
    parser.error("File does not exist: {}".format(x))


def main():
    parser = argparse.ArgumentParser(
               description="Process the dataset (fMRI"
                           " sequence) with mcflirt and converts the result"
                           " to the format used by ovmc.")
    parser.add_argument("algorithm", action="store", help="Motion correction"
                        "algorithm to use",
                        choices=["mcflirt", "mcflirt_fudge",
                                 "niaklike", "niaklike_no_chained_init", "spm"])
    parser.add_argument("dataset", help="fMRI dataset to process.",
                        type=lambda x: check_file(parser, x))
    parser.add_argument("output_file", help="Output file where the "
                        "transformation parameters (tx, ty, tz, rx, ry,"
                        " rz) will be written.",
                        type=lambda x: check_file(parser, x))
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO,
                        format='INFO:%(asctime)s %(message)s')
    algorithms = {
        "mcflirt": mcflirt,
        "mcflirt_fudge": mcflirt_fudge,
        "niaklike": niaklike,
        "niaklike_no_chained_init": niaklike_no_chained_init,
        "spm": spm
    }
    algorithms[args.algorithm](args.dataset, args.output_file)


if __name__ == '__main__':
    main()
