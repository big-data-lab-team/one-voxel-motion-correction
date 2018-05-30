#!/usr/bin/env python

import subprocess
import argparse
import os
import shutil
import logging
from logging import info
from logging import error
import transfo_utils as tu
import tempfile


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
        raise Exception("Command failed (return"
                        " code was {})".format(process.returncode))
    return stdout.decode("utf-8")


def spm(dataset, output_file_name):
    path, fil = os.path.split(__file__)
    template_file = os.path.join(path, "spm_template.m")

    with open(template_file) as f:
        template_string = f.read()

    template_string = template_string.replace('[SPM_INSTALL]', '/spm')
    template_string = template_string.replace('[DATASET]', dataset)
    script_file = tempfile.NamedTemporaryFile(delete=False)
    script_file.write(template_string)
    script_file.close()
    run_command("octave {}".format(script_file.name))
    # Put the results in the right format
    assert(os.path.exists(output_file_name))
    os.unlink(script_file)


def extract_mnc_volume(func_name, func_image_mnc, i):
    vol_name = "{}_vol_{}.mnc".format(func_name, i)
    run_command("mincreshape -clobber -dimrange time={} {} {}"
                .format(i, func_image_mnc, vol_name))
    return vol_name


def niaklike(dataset, output_file_name, chained_init=True):

    # Convert dataset to mnc
    func_name = output_file_name.replace('.nii', '').replace('.gz', '')
    func_image_mnc = func_name + ".mnc"
    if not os.path.exists(func_image_mnc):
        func_image_nii = func_name + '.nii'
        if not os.path.exists(func_image_nii):
            # It must be a .nii.gz
            run_command("gunzip {}".format(dataset))
            assert(os.path.exists(func_image_nii))
        run_command("nii2mnc {} {}".format(func_image_nii, func_image_mnc))
        assert(os.path.exists(func_image_mnc))

    # Get reference volume
    n_vols = int(run_command("mincinfo -dimlength"
                             " time {}").format(func_image_mnc))
    n_ref_vol = nvols / 2

    # Extract reference volume
    ref_vol_name = extract_mnc_volume(func_name, func_image_mnc, n_ref_vol)
    minctrac_opts = ("-clobber -xcorr -forward -lsq6 -speckle 0 -est_center"
                     " -tol 0.0005  -trilinear -simplex 10 -model_lattice "
                     "-step 10 10 10")

    # Create identity transformation
    run_command("param2xfm -clobber identity.xfm -translation 0 0 0"
                " -rotations 0 0 0 -clobber")
    init_transfo = 'identify.xfm'

    # Registration
    for i in range(0, n_vols):

        # Extract volume from sequence
        vol_name = extract_mnc_volume(func_name, func_image_mnc, i)
        if not os.path.exists(vol_name):
            run_command("mincreshape -clobber -dimrange time={} {} {}"
                        .format(i, func_image_mnc, vol_name))
        output_transfo = "{}_transf_{}_{}.xfm".format(func_name,
                                                      i,
                                                      n_ref_vol)

        # Register volume to reference volume
        command = ("minctracc {} {} {} -transformation {} {}"
                   .format(vol_name, ref_vol_name, output_transfo,
                           init_transfo, minctrac_opts))
        run_command(command)
        assert(os.path.exists(output_transfo))

        # Write transformation to output file
        transfo_vector = tu.get_transfo_vector(tu.read_transfo(output_transfo))
        with open(output_file_name, 'a') as output_file:
            output_file.write(transfo_vector)

        # Initialize next registration
        if chained_init:
            init_transfo = output_transfo


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
    parser.add_argument("spm_path", help="Path to SPM12 installation,"
                        " used by spm algorithm.",
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
