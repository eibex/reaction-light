FROM python:3.9

RUN apt-get update
RUN apt-get install -y --no-install-recommends \
        libatlas-base-dev libssl-dev libffi-dev git openssl python3-openssl

COPY ./ /bot/

RUN python3.9 -m pip install -r /bot/requirements.txt

# Remove local copies as these files gets mounted instead.
RUN rm -r /bot/files
RUN rm -r /bot/config.ini

WORKDIR /bot

CMD ["python3.9", "bot.py"]