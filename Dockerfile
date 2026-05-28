# Stage 1: Build the React frontend
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# Stage 2: Serve the application using Django
FROM python:3.11-slim
WORKDIR /app

# Install system dependencies for compiling python packages (e.g. psycopg2)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend application files
COPY backend/ ./backend/

# Copy compiled frontend build from Stage 1
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Expose port (Railway dynamically injects PORT)
ENV PORT=8000
EXPOSE 8000

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV DEBUG=False

WORKDIR /app/backend

# Collect static files into the Django build folder
RUN python manage.py collectstatic --noinput

# Run migrations and start Gunicorn WSGI server
CMD python manage.py migrate && gunicorn breathe_esg.wsgi:application --bind 0.0.0.0:$PORT
