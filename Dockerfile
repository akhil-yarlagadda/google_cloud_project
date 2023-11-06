FROM python:3.11-alpine3.15
WORKDIR /app
COPY Flask_Project-2 /app
RUN pip install --upgrade pip
RUN pip install --upgrade setuptools
RUN pip install --trusted-host pypi.python.org -r requirements.txt -v
EXPOSE 8080
CMD python ./cloud_storage.py