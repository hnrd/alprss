FROM reg.zknt.org/zknt/python

COPY requirements.txt /app/requirements.txt
WORKDIR /app
RUN apk add --no-cache gdbm gcc libxml2 libxslt libxml2-dev musl-dev libxslt-dev python3-dev && pip3 install -r requirements.txt && apk del gcc libxml2-dev musl-dev libxslt-dev python3-dev

COPY . /app
ENV FLASK_APP=app.py
VOLUME /data
EXPOSE 5000
ENTRYPOINT flask run --host=0.0.0.0
