# one-voxel-motion-correction

Software used for a one-voxel experiment on fMRI motion estimation.


## Contents

* `ovmc`: Python package with functions to call AFNI's, SPM's, FSL's and
  Niak's motion estimation tools and output results in a common format. Can
  also bootstrap any of these functions through one-voxel perturbation.

* `bin`: binaries and scripts used in the experiment. Used in `Dockerfile`.
  FSL's `mcflirt` and SPM are embeded here directly, for simplicity. AFNI is
  downloaded and installed on-the-fly in the container. `spm_brick_realign.m` is
  copied from https://github.com/SIMEXP/spm_pipe. `niak_*_no_chained.m` is a modified
  copy from Niak-cog.

* `ovmc.json`: a [Boutiques](http://boutiques.github.io) descriptor for `ovmc`,
  with tests!

* `test/data`: data used in the tests.

## Demo

This will soon be converted to a Jupyter notebook. For now, hey, it's 
plain markdown!

For a quick demo, you don't have to clone this repository. Instead, just
get `ovmc.json` and run:
* `pip install boutiques`
* `bosh test ovmc.json`

This will produce files called `output_<algo>.{par,fd}`, for the test 
dataset and a perturbated version of it. `par` files contain the motion 
parameters estimated with `<algo>` in the form `tx ty tz rx ry rz` 
where translations are in mm and rotations are in radians. Actually we're not
quite sure if the rotation parameters are in the right order for all methods, but
we don't really mind since we will use the frame displacements (FD) as metric
. `fd` files 
contain frame displacements, in mm. The test will also produce 
`output_<algo>_diff.{par,fd}` files which relate to the difference 
(computed as T1oT2-1) between the motion parameters estimated on the 
original and the perturbated datasets. 

These files can then be used to generate the plots below using `plots/plot.gnplt`
using [Gnuplot](http://gnuplot.info).

## Plots

### Comparing algorithms

With this graph we checked that we used the motion estimation algorithms 
correctly: all algorithms produce different but correlated results,
which is reassuring.

[all_algos_fd](https://github.com/big-data-lab-team/one-voxel-motion-correction/raw/master/plots/all_algos_fd.png)

### Stability to one-voxel perturbation

This illustrate the main result of our study. FSL and Niak are quite 
sensitive to the one-voxel perturbation, while AFNI and SPM are not.
This is due to the use of chained initializations (between volumes and 
between resolutions) in FSL and Niak.

[all_algos_diff_fd](https://github.com/big-data-lab-team/one-voxel-motion-correction/raw/master/plots/all_algos_diff_fd.png)
