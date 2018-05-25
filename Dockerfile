from simexp/minc-toolkit

RUN apt-get install -y\
  python-setuptools &&\
  easy_install pip &&\
  mkdir /test

ADD . .
ADD bin/mcflirt /bin
ADD test/data/test.nii.gz /test
RUN  pip install .
