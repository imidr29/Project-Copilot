# Use official Python 3.10 image
FROM python:3.10-slim

# Set working directory in container
WORKDIR /app

# Copy requirements file (if you have one)
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your project
COPY . .

# Set environment variables (optional defaults)
ENV OPENAI_API_KEY=""
ENV PINECONE_API_KEY=""
ENV MYSQL_URL="mysql+pymysql://root:password@mysql:3306/ops_db"

# Command to run your app (replace main_app.py with your entrypoint)
CMD ["python", "main_app.py"]
