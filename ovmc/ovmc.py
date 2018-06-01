#!/usr/bin/env python

import subprocess
import argparse
import os
import shutil
import logging
import tempfile
import transfo_utils as tu
from logging import info
from logging import error
from termcolor import colored
from ovmc import transfo_utils as tu
from ovmc import one_voxel as ov
import tempfile


def run_command(command):
    info(command)
    process = subprocess.Popen(command, shell=True,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
    (stdout, stderr) = process.communicate()
    if stdout.strip() != "":
        print(colored(stdout.decode("utf-8"), "green"))
    if stderr.strip() != "":
        print(colored(stderr.decode("utf-8"), "red"))
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
    # TODO Put the results in the right format
    assert(os.path.exists(output_file_name))
    os.unlink(script_file)


def extract_mnc_volume(func_name, func_image_mnc, i):
    vol_name = "{}_vol_{}.mnc".format(func_name, i)
    if not os.path.exists(vol_name):
        run_command("mincreshape -clobber -dimrange time={} {} {}"
                    .format(i, func_image_mnc, vol_name))
    return vol_name


def niaklike(dataset, output_file_name, chained_init=True):

    # Convert dataset to mnc
    func_name = dataset.replace('.nii', '').replace('.gz', '')
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
    command = ("mcflirt -in {} -out {} -plots "
               " -spline_final".format(dataset, output_name))
    if fudge:
        command += " -fudge"
    run_command(command)


def check_file(parser, x):
    if os.path.exists(x):
        return x
    parser.error("File does not exist: {}".format(x))


def write_average(param_files, average_param_file):
    average_transfos = None
    n_vols = -1
    for param_file in param_files:
        transfos = {}
        with open(param_file) as f:
            param_file_transfos = f.readlines()
        for param_file_transfo in param_file_transfos:
            if param_file_transfo.strip() == "":
                continue
            a = param_file_transfo.split(" ")
            assert(len(a) == 6)
            transfos.append([float(a[0]),
                             float(a[1]),
                             float(a[2]),
                             float(a[3]),
                             float(a[4]),
                             float(a[5])])
        if n_vols == -1:
            n_vols = len(transfos)
        assert(len(transfos) == n_vols)
        if average_transfos is None:
            average_transfos = transfos
        else:
            for i in range(0, n_vols):
                for j in range(0, 6):
                    average_transfos[i][j] += transfos[i][j]
    for i in range(0, n_vols):
        for j in range(0, 6):
            average_transfos[i][j] /= len(param_files)
    with open(average_param_file, 'w') as f:
        for t in average_transfos:
            f.write("{} {} {} {} {} {}{}".format(t[0],
                                                 t[1],
                                                 t[2],
                                                 t[3],
                                                 t[4],
                                                 t[5],
                                                 os.linesep))


def bootstrap_algo(algorithms, algo_name, n_samples,
                   dataset, output_name):
    func_name = dataset.replace('.nii', '').replace('.gz', '')
    output_files = []
    for n in range(0, n_samples):
        info("Iteration {}".format(n))

        # Add noise to functional image
        noised_image = "{}-iter-{}.nii.gz".format(func_name, n)
        ov("{} {} --random".format(dataset, noised_image))
        assert(os.path.exists(noised_image))

        # Run the motion estimation
        output_transfo_file = "{}_iter_{}.par".format(output_name, n)
        algorithms[algo_name](noised_image, output_transfo_file)
        output_files.add(output_transfo_file)

        # Compute partial average
        output_transfo_file = "{}_average_{}.par"
        write_average(output_files, output_transfo_file)


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
    parser.add_argument("--bootstrap", help="Runs an one-voxel experiment"
                                            " with the specified number "
                                            "of bootstrap samples.",
                        action="store")
    parser.add_argument("spm_path", help="Path to SPM12 installation,"
                        " used by spm algorithm.",
                        type=lambda x: check_file(parser, x))
    parser.add_argument("output_name", help="Output file name. .par files "
                        "containing transformation parameters "
                        "(tx, ty, tz, rx, ry,"
                        " rz) will be written for every bootstrap iteration.")
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
    if os.path.exists(output_file_name):
        shutil.rmtree(output_file_name)
    if args.boostrap:
        bootstrap_algo(algorithms, args.algorithm,
                       args.bootstrap, args.dataset, args.output_name)
    else:
        algorithms[args.algorithm](args.dataset, args.output_name+".par")


if __name__ == '__main__':
    main()
