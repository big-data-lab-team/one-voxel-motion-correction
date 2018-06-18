from simexp/niak-cog

RUN apt-get install -y\
  python-setuptools python-dev &&\
  easy_install pip &&\
  mkdir /test && mkdir /ovmc

RUN (mkdir /usr/local/afni; cd /usr/local/afni;\
     wget wget https://afni.nimh.nih.gov/pub/dist/tgz/linux_ubuntu_16_64.tgz ;\
     tar zxvf linux_ubuntu_16_64.tgz ; rm linux_ubuntu_16_64.tgz)
ENV PATH=$PATH:/usr/local/afni/linux_ubuntu_16_64

ADD bin/niak_brick_motion_parameters.m /usr/local/niak/bricks/fmri_preprocess/
ADD bin/mcflirt /bin
ADD bin/spm_brick_realign.m /usr/local/niak/bricks
ADD bin/psom_defaults.m /usr/local/niak/bricks
ADD test/data/test.nii.gz /test
ADD ovmc /ovmc/ovmc
ADD setup.py /ovmc
RUN (cd /ovmc && ls && pip install .)
