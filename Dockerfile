# Use Python as the base image
FROM python:3.11

# Update package list 
RUN apt-get update 

# Install supervisor
RUN apt-get install -y supervisor 


# Set work directory
WORKDIR /

COPY requirements.txt .

# Copy requirements file and install Python dependencies
RUN python3 -m pip install --upgrade pip
RUN python3 -m pip install --upgrade setuptools
RUN python3 -m pip install -r requirements.txt 

# Copy application code
COPY . .
# Run django's python manage.py and migrate commands
RUN python3 zavmo/manage.py makemigrations --noinput
RUN python3 zavmo/manage.py migrate
#RUN python3 squizzy/manage.py createsuperuser --noinput || true
RUN python3 zavmo/manage.py createsuperuser --noinput 


# Start supervisor
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
