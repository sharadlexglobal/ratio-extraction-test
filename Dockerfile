# opennyai 0.0.15 requires Python >=3.13; on an older base pip silently falls
# back to an ancient release whose pinned tokenizers has no wheel and needs a
# Rust toolchain to build. Matching the interpreter avoids all of that.
FROM python:3.13-slim
RUN apt-get update -qq && apt-get install -y -qq --no-install-recommends \
      build-essential ca-certificates curl git && rm -rf /var/lib/apt/lists/*
WORKDIR /app
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir opennyai
COPY run_test.py .
CMD ["python", "-u", "run_test.py"]
