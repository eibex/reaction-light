FROM python:3.9

COPY ./ /bot/

RUN python3.9 -m pip install -r /bot/requirements.txt

# Remove local copies as these files get mounted instead.
RUN rm -r /bot/files

WORKDIR /bot

CMD ["python3.9", "-u", "bot.py"]
