FROM python:3

COPY . .

RUN python3 -m pip install --no-cache-dir -r requirements.txt

RUN python3 setup.py install
