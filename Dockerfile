# Use an official Python runtime as the base image
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file to the working directory
COPY myapp/requirements.txt .

# Install the app dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the app code to the working directory
COPY myapp/app.py .

# Expose the desired port
EXPOSE 5001

HEALTHCHECK --interval=12s --timeout=3s \
  CMD curl -f http://localhost:5000/health || exit 1
# Define the command to run your app
CMD ["python", "app.py"]
