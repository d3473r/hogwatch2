FROM python:3.7-stretch
EXPOSE 8765
COPY ./ /root/hogwatch2/
RUN apt-get update && apt-get install -y libpcap-dev && pip install websockets janus
CMD cd /root/hogwatch2/ && python hogwatch2.py