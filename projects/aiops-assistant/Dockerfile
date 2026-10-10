FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py agent.py guardrails.py remediation.py ./
COPY schemas/ schemas/
# fetch_metrics and fetch_health run in-process (agent.py); fetch_logs stays a Lambda
COPY lambda/fetch_metrics/lambda_function.py lambda/fetch_metrics/
COPY lambda/fetch_health/lambda_function.py lambda/fetch_health/

RUN useradd --create-home --uid 10001 kira
USER 10001

EXPOSE 8501

CMD ["streamlit", "run", "app.py", \
     "--server.port=8501", "--server.address=0.0.0.0", \
     "--server.headless=true", "--browser.gatherUsageStats=false"]
