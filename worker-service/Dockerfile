FROM python:3.10-slim

WORKDIR /app

RUN pip install uv

COPY requirements.txt .

RUN uv pip install --system --no-cache-dir -r requirements.txt

# Install Chromium AND its system dependencies in one go!
RUN playwright install chromium && playwright install-deps chromium

COPY . .

EXPOSE 8000

# Run FastAPI with Uvicorn
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]