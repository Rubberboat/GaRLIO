FROM python:3.11-slim-bookworm
ENV MPLBACKEND=Agg PYTHONUNBUFFERED=1
WORKDIR /opt/research
COPY docker/analysis/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt \
    && pip freeze > /opt/research/build-python.txt
COPY . /opt/research
CMD ["python", "-c", "import evo, rosbags, numpy, scipy, pandas, matplotlib; print('analysis imports OK')"]
