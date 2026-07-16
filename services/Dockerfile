FROM python:3.11-slim

ARG SERVICE_NAME
ARG SERVICE_PORT=8000

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY shared /app/shared
COPY ml /app/ml
COPY services/${SERVICE_NAME} /app/services/${SERVICE_NAME}

ENV PYTHONPATH=/app

# Train domain models at image build
RUN if [ "$SERVICE_NAME" = "energy" ]; then python -m ml.energy.train_rul; fi
RUN if [ "$SERVICE_NAME" = "quality" ]; then python -m ml.quality.train_anomaly; fi
RUN if [ "$SERVICE_NAME" = "demand" ]; then python -m ml.demand.train_forecast; fi
RUN if [ "$SERVICE_NAME" = "supply" ]; then python -m ml.supply.train_price; fi
RUN if [ "$SERVICE_NAME" = "sales" ]; then python -m ml.sales.train_forecast; fi
RUN if [ "$SERVICE_NAME" = "finance" ]; then python -m ml.finance.train_cashflow; fi

ENV SERVICE_NAME=${SERVICE_NAME}
ENV SERVICE_PORT=${SERVICE_PORT}

EXPOSE ${SERVICE_PORT}

HEALTHCHECK --interval=30s --timeout=5s --start-period=25s --retries=3 \
  CMD curl -f http://localhost:${SERVICE_PORT}/health || exit 1

CMD ["sh", "-c", "uvicorn services.${SERVICE_NAME}.main:app --host 0.0.0.0 --port ${SERVICE_PORT}"]
