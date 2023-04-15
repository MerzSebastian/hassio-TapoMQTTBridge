ARG BUILD_FROM
FROM $BUILD_FROM

# Install requirements for add-on
RUN apk add --no-cache python3
RUN apk add --no-cache py3-pip
RUN apk add --no-cache gcc musl-dev python3-dev

# Copy data for add-on
COPY adapter.py /
COPY requirements.txt /
COPY device.json /
RUN chmod a+x /adapter.py
RUN chmod a+x /requirements.txt
RUN chmod a+x /device.json

# Install requirements
RUN pip3 install -r requirements.txt

CMD ["/usr/bin/with-contenv", "exec", "python3", "adapter.py"]