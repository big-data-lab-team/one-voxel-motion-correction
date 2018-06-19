from simexp/niak-cog

RUN apt-get install -y\
  python-setuptools python-dev &&\
  easy_install pip &&\
  mkdir /test && mkdir /ovmc

# AFNI
RUN (mkdir /usr/local/afni; cd /usr/local/afni;\
     wget wget https://afni.nimh.nih.gov/pub/dist/tgz/linux_ubuntu_16_64.tgz ;\
     tar zxvf linux_ubuntu_16_64.tgz ; rm linux_ubuntu_16_64.tgz)
ENV PATH=$PATH:/usr/local/afni/linux_ubuntu_16_64

# Niak
ADD bin/niak_brick_motion_parameters_no_chained.m /usr/local/niak/bricks/fmri_preprocess/
ADD bin/niak_pipeline_motion_no_chained.m /usr/local/niak/pipeline/

# FSL
ADD bin/mcflirt /bin
ENV FSLOUTPUTTYPE=NIFTI_GZ

# SPM
ADD bin/spm_brick_realign.m /usr/local/niak/bricks
ADD bin/psom_defaults.m /usr/local/niak/bricks

# TEST DATA
ADD test/data/test.nii.gz /test
ADD test/data/test_one_voxel.nii.gz /test

# OVMC
ADD ovmc /ovmc/ovmc
ADD setup.py /ovmc
RUN (cd /ovmc && ls && pip install .)
