FROM python:3.12

COPY ./ /bot/

RUN python3.12 -m pip install -r /bot/requirements.txt

# Remove local copies as these files get mounted instead.
RUN rm -r /bot/files

WORKDIR /bot

CMD ["python3.12", "-u", "bot.py"]
