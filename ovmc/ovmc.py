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


def write_fds(transfo_file, fd_file_name):
    with open(transfo_file) as f:
        transfos = f.readlines()
    with open(fd_file_name, 'w') as fd_file:
        for t in transfos:
            transfo = parse_transfo(t)
            fd = tu.framewise_displacement(transfo)
            fd_file.write(str(fd)+os.linesep)


def cleanup(files):
    for f in files:
        if os.path.exists(f):
            os.remove(f)


# Motion estimation


def spm(dataset, output_file_name):
    path, fil = os.path.split(__file__)
    template_file = os.path.join(path, "spm_template.m")

    with open(template_file) as f:
        template_string = f.read()

    temp_file_1 = tempfile.NamedTemporaryFile(delete=False)
    temp_file_2 = tempfile.NamedTemporaryFile(delete=False)

    template_string = template_string.replace('[SPM_INSTALL]', '/spm')
    template_string = template_string.replace('[DATASET]', dataset)
    template_string = template_string.replace('[OUTPUT_FILE_NAME]',
                                              output_file_name)
    template_string = template_string.replace('[TEMP_FILE_1]', temp_file_1.name)
    template_string = template_string.replace('[TEMP_FILE_2]', temp_file_2.name)
    script_file = tempfile.NamedTemporaryFile(delete=False)
    script_file.write(template_string.encode())
    script_file.close()
    run_command("octave {}".format(script_file.name))
    assert(os.path.exists(output_file_name))
    os.unlink(script_file.name)
    os.unlink(temp_file_1.name)
    os.unlink(temp_file_2.name)


def niak(dataset, output_file_name, chained=True):
    path, fil = os.path.split(__file__)
    template_file = os.path.join(path, "niak_template.m")
    tempdir = tempfile.mkdtemp()

    with open(template_file) as f:
        template_string = f.read()

    n_volumes = n_vols(dataset)
    template_string = template_string.replace('[DATASET]', dataset)
    template_string = template_string.replace('[FOLDER_OUT]', tempdir)
    template_string = template_string.replace('[N_VOLS]', str(n_volumes))
    if chained:
        template_string = template_string.replace('[CHAINED]', '')
    else:
        template_string = template_string.replace('[CHAINED]', '_no_chained')
    script_file = tempfile.NamedTemporaryFile(delete=False)
    script_file.write(template_string.encode())
    script_file.close()
    run_command("octave {}".format(script_file.name))

    # Put the results in the right format and file
    with open(output_file_name, 'w') as output_file:
        for i in range(1, n_volumes+1):
            output_transfo = os.path.join(tempdir, 'transf_{}.xfm'.format(i))
            transfo = tu.read_transfo(output_transfo)
            transfo_vector = tu.get_transfo_vector(transfo)
            write_params(transfo_vector, output_file)
    cleanup(['identity.xfm'])

def niak_no_chained_init(dataset, output_file_name):
    return niak(dataset, output_file_name, chained=False)


def mcflirt_fudge(dataset, output_file_name):
    return mcflirt(dataset, output_file_name, True)


def mcflirt(dataset, output_file_name, fudge=False):
    # Run mcflirt
    output_file_name = output_file_name.replace('.par', '')
    command = ("mcflirt -in {} -out {} "
               " -plots".format(dataset, output_file_name))
    if fudge:
        command += " -fudge"
    run_command(command)
    cleanup([output_file_name + '.nii.gz'])


def afni(dataset, output_file_name):
    command = ("3dvolreg -1Dfile {} -base {} {}".format(output_file_name,
                                                        int(n_vols(dataset)/2),
                                                        dataset))
    run_command(command)
    cleanup(['volreg+orig.HEAD', 'volreg+orig.BRIK'])


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
    func_name = dataset.replace('.nii', '').replace('.gz', '')
    output_files = []
    for n in range(0, n_samples):
        info("Bootstratp iteration #{}".format(n))

        # Add noise to functional image
        noised_image = "{}-iter-{}.nii.gz".format(func_name, n)
        ov([dataset, noised_image, "--random"])
        assert(os.path.exists(noised_image))

        # Run the motion estimation
        output_transfo_file = "{}_titer_{}.par".format(output_name, n)
        algo_func(noised_image, output_transfo_file)
        write_fds(output_transfo_file, "{}_titer_{}.fd".format(output_name, n))
        output_files.append(output_transfo_file)

        # Compute partial average
        output_transfo_file = "{}_average_{}.par".format(output_name, n_samples)
        write_average(output_files, output_transfo_file)


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
                        " be available in /spm.",
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

    # Put motion estimation algorithms in a dict of functions
    algorithms = {
            "mcflirt": mcflirt,
            "mcflirt_fudge": mcflirt_fudge,
            "niak": niak,
            "niak_no_chained_init": niak_no_chained_init,
            "spm": spm,
            "afni": afni
        }
    if args.bootstrap:
        for algo in algorithms.keys():
            algorithms[algo] = (lambda dataset, output_file_name:
                                bootstrap_algo(algorithms[algo],
                                               int(args.bootstrap),
                                               args.dataset,
                                               args.output_name))

    # Remove output files if they already exist
    output_files = [
        args.output_name + '.par',
        args.output_name + '.fd',
        args.output_name + '_perturbated.par',
        args.output_name + '_perturbated.fd',
        args.output_name + '_diff.par',
        args.output_name + '_diff.fd'
    ]
    cleanup(output_files)

    # Original dataset
    output_name_1 = args.output_name + '.par'
    algorithms[args.algorithm](args.dataset, output_name_1)
    assert(os.path.exists(output_name_1))
    write_fds(output_name_1, args.output_name + '.fd')

    # Perturbated dataset
    output_name_2 = args.output_name + '_perturbated.par'
    algorithms[args.algorithm](args.dataset_perturbated, output_name_2)
    assert(os.path.exists(output_name_2))
    write_fds(output_name_2, args.output_name + '_perturbated.fd')

    # Difference
    with open(output_name_1) as f:
        transfos_1 = f.readlines()
    with open(output_name_2) as f:
        transfos_2 = f.readlines()
    assert(len(transfos_1) == len(transfos_2))
    with open(args.output_name + '_diff.fd', 'w') as fd_file:
        with open(args.output_name + '_diff.par', 'w') as par_file:
            for i in range(0, len(transfos_1)):
                t1 = parse_transfo(transfos_1[i])
                t2 = parse_transfo(transfos_2[i])
                diff = tu.diff_transfos(tu.get_transfo_mat(t1),
                                        tu.get_transfo_mat(t2))
                write_params(diff, par_file)
                fd = tu.framewise_displacement(diff)
                fd_file.write(str(fd)+os.linesep)


if __name__ == '__main__':
    main()
