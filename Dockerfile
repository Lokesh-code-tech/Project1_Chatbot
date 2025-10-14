# Use the official Python base image
FROM python:3.11-slim

# Set the working directory inside the container
WORKDIR /app

# Copy only requirements first (for caching)
COPY . /app

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose FastAPI default port
EXPOSE 7860

# Run the FastAPI app using uvicorn
# Replace "main:app" with your FastAPI filename and app instance
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "7860"]
