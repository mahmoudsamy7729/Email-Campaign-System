#setup server 

FROM python:3.11-slim


#show logs in real time
ENV PYTHONUNBUFFERED=1 


#update kernel + install dependices 
RUN apt-get update && apt-get -y install gcc libpq-dev


#create project folder : kernal 

WORKDIR /app

#copy requirements.txt
COPY requirements.txt /app/requirements.txt

#install python dependices
RUN pip install -r /app/requirements.txt

# copy porject code ----> docker
COPY . /app
