FROM python:3.10-slim

# Set the working directory
WORKDIR /code

# Copy requirements and install dependencies
COPY ./requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

# Hugging Face Spaces run as a non-root user with ID 1000
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

WORKDIR $HOME/app

# Copy the application files
COPY --chown=user . $HOME/app

# Expose the port Hugging Face uses
EXPOSE 7860

# Command to run the Flask application via Gunicorn
CMD ["gunicorn", "-b", "0.0.0.0:7860", "app:app"]
