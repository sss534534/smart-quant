FROM python:3.10-slim

WORKDIR /app

COPY services/strategy-engine/requirements.txt ./requirements.txt
COPY services/common/requirements.txt ./common-requirements.txt
RUN pip install --no-cache-dir -r requirements.txt -r common-requirements.txt

COPY services/common ./common
COPY services/strategy-engine/ .

ENV PYTHONPATH=/app

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
