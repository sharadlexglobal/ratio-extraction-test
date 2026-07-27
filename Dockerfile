FROM python:3.11-slim
RUN apt-get update -qq && apt-get install -y -qq --no-install-recommends \
      poppler-utils ca-certificates && rm -rf /var/lib/apt/lists/*
WORKDIR /app
RUN pip install --no-cache-dir scikit-learn scipy numpy
COPY run_test.py .
CMD ["python", "-u", "run_test.py"]
