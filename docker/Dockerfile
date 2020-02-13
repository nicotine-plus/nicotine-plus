# Usage examples:
# docker build -t nicotine -f docker/Dockerfile
# docker run --net=host --env="DISPLAY" --volume="$HOME/.Xauthority:/root/.Xauthority:rw" -t nicotine
# docker exec -it <ID> ptpython
# docker exec -it -e DISPLAY=$DISPLAY <ID> xterm

FROM ubuntu:18.04

RUN apt update
RUN apt install -y python3 python3-pip python3-virtualenv libgtk-3-0 miniupnpc python-gobject-2 python-mutagen xdg-utils libcairo2-dev libgirepository1.0-dev python3-gi gobject-introspection gir1.2-gtk-3.0 xterm


WORKDIR /nicotine
COPY . /nicotine

ENV VIRTUAL_ENV=./nicotine-venv
RUN python3 -m virtualenv --python=/usr/bin/python3 $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

RUN pip install pip virtualenv
RUN pip install ptpython pygobject mutagen

CMD ./nicotine || sleep 100000

