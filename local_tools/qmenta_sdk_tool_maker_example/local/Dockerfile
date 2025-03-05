FROM qmentasdk/minimal:latest

ENV WORKDIR "/root/"

RUN apt-get update
RUN apt-get install -y python3-pip python-dev build-essential libfreetype6-dev libxft-dev wkhtmltopdf xvfb
RUN pip install --upgrade pip \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*
# Does it require any specific 3rd party tool? Install here.

# A virtual x framebuffer is required to generate PDF files with pdfkit
RUN echo '#!/bin/bash\nxvfb-run -a --server-args="-screen 0, 1024x768x24" /usr/bin/wkhtmltopdf -q $*' > /usr/bin/wkhtmltopdf.sh && \
    chmod a+x /usr/bin/wkhtmltopdf.sh && \
    ln -s /usr/bin/wkhtmltopdf.sh /usr/local/bin/wkhtmltopdf
# Install requirements and dependencies (both treated as normal python packages)
COPY requirements.txt ${WORKDIR}/requirements.txt

RUN pip install -r ${WORKDIR}/requirements.txt

# Add tool script
RUN mkdir -p ${WORKDIR}/
COPY tool.py ${WORKDIR}/tool.py
COPY report_template.html ${WORKDIR}/report_template.html

# Configure entrypoint
RUN ln -fs /usr/bin/python3 /usr/bin/python \
    && ln -fs /usr/bin/pip3 /usr/bin/pip

RUN python -m qmenta.sdk.make_entrypoint ${WORKDIR}/entrypoint.sh ${WORKDIR}/
RUN chmod +x ${WORKDIR}/entrypoint.sh