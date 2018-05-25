from simexp/minc-toolkit

RUN apt-get install -y\
  python-setuptools &&\
  easy_install pip

ADD . .
ADD bin/mcflirt /bin
RUN  pip install .
