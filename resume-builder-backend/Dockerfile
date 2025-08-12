FROM python:3.11-slim

# Install LaTeX (texlive) for PDF generation
RUN apt-get update && \
    apt-get install -y texlive-latex-base texlive-latex-extra texlive-fonts-recommended && \
    rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code including templates
COPY ./app /app/app

# Environment variable for template path
ENV TEMPLATE_PATH=/app/app/templates

# Expose backend port
EXPOSE 8000

# Start the server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
