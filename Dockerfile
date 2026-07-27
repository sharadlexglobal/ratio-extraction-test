FROM python:3.11-slim
RUN apt-get update -qq && apt-get install -y -qq --no-install-recommends \
      build-essential ca-certificates curl && rm -rf /var/lib/apt/lists/*
WORKDIR /app
RUN pip install --no-cache-dir opennyai
COPY run_test.py .
CMD ["python", "-u", "run_test.py"]
