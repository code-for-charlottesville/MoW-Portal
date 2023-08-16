FROM surnet/alpine-wkhtmltopdf:3.15.0-0.12.6-small as wkhtmltopdf

FROM python:3.10.4-alpine3.15

# Install dependencies for wkhtmltopdf
RUN apk add --no-cache \
  libstdc++ \
  libx11 \
  libxrender \
  libxext \
  libssl1.1 \
  ca-certificates \
  fontconfig \
  freetype \
  ttf-dejavu \
  ttf-droid \
  g++ \
  ttf-freefont \
  ttf-liberation \
  postgresql-dev \
  bash \
  xvfb \
&& apk add --no-cache --virtual .build-deps \
  msttcorefonts-installer \
\
# Install microsoft fonts
&& update-ms-fonts \
&& fc-cache -f \
\
# Clean up when done
&& rm -rf /tmp/* \
&& apk del .build-deps \
# Import code and pip install
&& pip install --upgrade pip \
&& mkdir /code

# Copy wkhtmltopdf files from docker-wkhtmltopdf image
COPY --from=wkhtmltopdf /bin/wkhtmltopdf /bin/wkhtmltopdf

WORKDIR /code
ADD requirements.txt /code/
RUN pip3 install -r requirements.txt
