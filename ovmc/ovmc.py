#!/usr/bin/env python

import subprocess
import argparse
import os
import shutil
import logging
import tempfile
from logging import info
from logging import error
from termcolor import colored
from ovmc import transfo_utils as tu
from ovmc import one_voxel as ov
import tempfile
import nibabel
import math

# Utils


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


def n_vols(dataset):
    im = nibabel.load(dataset)
    shape = im.header.get_data_shape()
    if len(shape) < 4:
        return 1
    return shape[3]


def write_params(params, param_file):
    assert(len(params) == 6)
    param_file.write("{} {} {} {} {} {}".format(params[0],
                                                params[1],
                                                params[2],
                                                params[3],
                                                params[4],
                                                params[5]) +
                     os.linesep)


def compute_fd(params, previous_params):
    # convert angles to mm
    for i in range(3, 6):
        params[i] = (params[i] / 360) * 2 * math.pi * 50
        previous_params[i] = (previous_params[i] / 360) * 2 * math.pi * 50
    absdiff = [abs(params[i]-previous_params[i]) for i in range(0, 6)]
    return sum(absdiff)


def write_fds(transfo_file):
    fd_file_name = os.path.splitext(transfo_file)[0] + '.fd'
    with open(transfo_file) as f:
        transfos = f.readlines()
    with open(fd_file_name, 'w') as fd_file:
        pt = None  # params at the previous time point
        for transfo_line in transfos:
            t = parse_transfo(transfo_line)
            if pt is not None:
                fd = compute_fd(t, pt)
                fd_file.write(str(fd)+os.linesep)
            pt = t


def cleanup(files):
    for f in files:
        if os.path.exists(f):
            os.remove(f)


def convert_from_mcflirt(mcflirt_file, standard_file):
    with open(mcflirt_file) as f:
        transfos = f.readlines()
    with open(standard_file, 'w') as f:
        for t in transfos:
            # mcflirt produces files formated as rx, ry, rz, x, y, z
            # with the rotation angles in radians
            [rx, ry, rz, x, y, z] = parse_transfo(t)
            write_params([x, y, z,
                          rx*180.0/math.pi,
                          ry*180.0/math.pi,
                          rz*180.0/math.pi], f)


# Motion estimation

def templated_octave_algo(template_file, substitutions):
    with open(template_file) as f:
        template_string = f.read()
    for key in substitutions.keys():
        template_string = template_string.replace(key, substitutions[key])
    script_file = tempfile.NamedTemporaryFile(delete=False)
    script_file.write(template_string.encode())
    script_file.close()
    run_command("octave {}".format(script_file.name))
    cleanup([script_file.name])


def spm(dataset, output_file_name):

    path, fil = os.path.split(__file__)
    template_file = os.path.join(path, "spm_template.m")
    temp_file_1 = tempfile.NamedTemporaryFile(delete=False)
    temp_file_2 = tempfile.NamedTemporaryFile(delete=False)

    substitutions = {
        '[SPM_INSTALL]': '/spm12',
        '[DATASET]': dataset,
        '[OUTPUT_FILE_NAME]': output_file_name,
        '[TEMP_FILE_1]': temp_file_1.name,
        '[TEMP_FILE_2]': temp_file_2.name
    }

    templated_octave_algo(template_file, substitutions)
    assert(os.path.exists(output_file_name))
    cleanup([temp_file_1.name, temp_file_2.name])
    return [output_file_name]


def niak(dataset, output_file_name, chained=True):
    path, fil = os.path.split(__file__)
    template_file = os.path.join(path, "niak_template.m")
    tempdir = tempfile.mkdtemp()
    n_volumes = n_vols(dataset)

    substitutions = {
        '[DATASET]': dataset,
        '[FOLDER_OUT]': tempdir,
        '[N_VOLS]': str(n_volumes),
        '[OUTPUT_FILE]': output_file_name
    }
    if chained:
        substitutions['[CHAINED]'] = ''
    else:
        substitutions['[CHAINED]'] = '_no_chained'

    templated_octave_algo(template_file, substitutions)

    cleanup(['identity.xfm'])
    return [output_file_name]


def niak_no_chained_init(dataset, output_file_name):
    return niak(dataset, output_file_name, chained=False)


def mcflirt_fudge(dataset, output_file_name):
    return mcflirt(dataset, output_file_name, True)


def mcflirt(dataset, output_file_name, fudge=False):
    # Run mcflirt
    output_file_name = output_file_name.replace('.par', '')
    command = ("mcflirt -in {} -out {} -refvol 0"
               " -plots".format(dataset, output_file_name + '_mcflirt'))
    if fudge:
        command += " -fudge"
    run_command(command)
    convert_from_mcflirt(output_file_name + '_mcflirt.par',
                         output_file_name + '.par')
    cleanup([output_file_name + '_mcflirt.nii.gz',
             output_file_name + '_mcflirt.par'])
    return [output_file_name + '.par']


def afni(dataset, output_file_name):
    command = ("3dvolreg -1Dfile {} -base 0 {}".format(output_file_name,
                                                       dataset))
    run_command(command)
    cleanup(['volreg+orig.HEAD', 'volreg+orig.BRIK'])
    return [output_file_name]


# Bootstrap


def write_average(param_files, average_param_file):
    average_transfos = None
    n_vols = -1
    for param_file in param_files:
        transfos = []
        with open(param_file) as f:
            param_file_transfos = f.readlines()
        for param_file_transfo in param_file_transfos:
            if param_file_transfo.strip() == "":
                continue
            a = parse_transfo(param_file_transfo)
            transfos.append(a)
        if n_vols == -1:
            n_vols = len(transfos)
        assert(len(transfos) == n_vols), "{} != {}".format(len(transfos),
                                                           n_vols)
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
            write_params(t, f)


def bootstrap_algo(algo_func, n_samples, dataset, output_name):
    output_name = output_name.replace('.par', '')
    func_name = dataset.replace('.nii', '').replace('.gz', '')
    output_files = []
    averages = []
    for n in range(0, n_samples):
        info("Bootstratp iteration #{}".format(n))

        # Add noise to functional image
        noised_image = "{}-iter-{}.nii.gz".format(func_name, n)
        ov([dataset, noised_image, "--random"])
        assert(os.path.exists(noised_image))

        # Run the motion estimation
        output_transfo_file = "{}_iter_{}.par".format(output_name, n)
        algo_func(noised_image, output_transfo_file)
        write_fds(output_transfo_file)
        output_files.append(output_transfo_file)

        # Compute partial average
        output_transfo_file = "{}_average_{}.par".format(output_name, n)
        write_average(output_files, output_transfo_file)
        averages.append(output_transfo_file)

        cleanup([noised_image])
    # Copy last iteration in final result
    shutil.copyfile(output_transfo_file, output_name+".par")
    averages.append(output_name+".par")

    return averages

# Parsing


def check_file(parser, x):
    if os.path.exists(x):
        return x
    parser.error("File does not exist: {}".format(x))


def parse_transfo(line):
    a = line.strip().replace('   ', ' ').replace('  ', ' ').split(" ")
    assert(len(a) == 6), ('Invalid transformation line: length is'
                          ' {}: {} - parsed: {}'.format(len(a), line, a))
    return [float(a[0]), float(a[1]), float(a[2]),
            float(a[3]), float(a[4]), float(a[5])]


# Main


def main():
    parser = argparse.ArgumentParser(
               description="Process the dataset (fMRI"
                           " sequence) with mcflirt and converts the result"
                           " to the format used by ovmc.")
    parser.add_argument("algorithm", action="store", help="Motion correction"
                        "algorithm to use. For spm, SPM12 installation has to"
                        " be available in /spm12.",
                        choices=["mcflirt", "mcflirt_fudge",
                                 "niak", "niak_no_chained_init", "spm", "afni"])
    parser.add_argument("dataset", help="fMRI dataset to process.",
                        type=lambda x: check_file(parser, x))
    parser.add_argument("dataset_perturbated", help="fMRI dataset to process,"
                        " modified with one-voxel perturbation.",
                        type=lambda x: check_file(parser, x))
    parser.add_argument("--bootstrap", help="Runs an one-voxel experiment"
                                            " with the specified number "
                                            "of bootstrap samples.",
                        action="store")
    parser.add_argument("output_name", help="Output file basename.")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO,
                        format='INFO:%(asctime)s %(message)s')

    # Define motion estimation function
    algorithm = globals()[args.algorithm]
    if args.bootstrap:
        algorithm = (lambda dataset, output_file_name:
                     bootstrap_algo(globals()[args.algorithm],
                                    int(args.bootstrap),
                                    dataset,
                                    output_file_name))

    # Remove output files if they already exist
    output_files = [
        args.output_name + '.par',
        args.output_name + '.fd',
        args.output_name + '_perturbated.par',
        args.output_name + '_perturbated.fd',
        args.output_name + '_diff.par',
        args.output_name + '_diff.fd'
    ]
    if args.bootstrap:
        output_files = []
        for i in range(0, int(args.bootstrap)):
            output_files.append(args.output_name +
                                '_iter_{}.par'.format(str(i)))
            output_files.append(args.output_name +
                                '_average_{}.par'.format(str(i)))
            output_files.append(args.output_name +
                                '_iter_{}.fd'.format(str(i)))
            output_files.append(args.output_name +
                                '_average_{}.fd'.format(str(i)))
            output_files.append(args.output_name +
                                '_perturbated_iter_{}.par'.format(str(i)))
            output_files.append(args.output_name +
                                '_perturbated_average_{}.par'.format(str(i)))
            output_files.append(args.output_name +
                                '_perturbated_iter_{}.fd'.format(str(i)))
            output_files.append(args.output_name +
                                '_perturbated_average_{}.fd'.format(str(i)))
    cleanup(output_files)

    # Original dataset
    output_name_1 = args.output_name + '.par'
    results_original = algorithm(args.dataset, output_name_1)
    for file_name in results_original:
        write_fds(file_name)

    # Perturbated dataset
    output_name_2 = args.output_name + '_perturbated.par'
    results_perturbated = algorithm(args.dataset_perturbated, output_name_2)
    for file_name in results_perturbated:
        write_fds(file_name)

    # Difference
    assert(len(results_original) == len(results_perturbated))
    for i in range(0, len(results_original)):
        # Read all the transfos
        with open(results_original[i]) as f:
            transfos_1 = f.readlines()
        with open(results_perturbated[i]) as f:
            transfos_2 = f.readlines()
        assert(len(transfos_1) == len(transfos_2))
        # Compute the differences
        output_name = os.path.splitext(results_original[i])[0]
        with open(output_name + '_diff.par', 'w') as par_file:
            for i in range(0, len(transfos_1)):
                # Compute difference transfo (T1oT2-1)
                t1 = parse_transfo(transfos_1[i])
                t2 = parse_transfo(transfos_2[i])
                diff = tu.diff_transfos(tu.get_transfo_mat(t1),
                                        tu.get_transfo_mat(t2))
                # Write parameters
                write_params(diff, par_file)
            # Write FDs
        write_fds(output_name + '_diff.par')


if __name__ == '__main__':
    main()
