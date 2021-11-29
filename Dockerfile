FROM python:3.8

RUN apt-get update
RUN apt-get install -y --no-install-recommends \
        libatlas-base-dev libssl-dev libffi-dev git openssl python3-openssl

COPY ./requirements.txt /bot/requirements.txt

RUN pip3 install -r /bot/requirements.txt

COPY ./ /bot/

# Files folder gets mounted instead.
RUN rm -r /bot/files

WORKDIR /bot

# Default configuration, arguments may be overriden on docker run
ENV NAME="Reaction Light"
ENV LOGO="https://cdn.discordapp.com/attachments/671738683623473163/693451064904515645/spell_holy_weaponmastery.jpg"
ENV COLOUR="0xffff00"
ENV LANGUAGE="en-gb"


CMD ["bash", "dockerstart.sh"]