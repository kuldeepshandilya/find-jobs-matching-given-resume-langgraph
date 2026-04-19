FROM python:3.12.7

WORKDIR /app

# Setup virtual env
RUN python -m venv /venv
ENV PATH="/venv/bin:$PATH"

RUN pip install --no-cache-dir --upgrade pip setuptools wheel

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 2024

CMD ["langgraph", "dev", "--allow-blocking", "--host", "0.0.0.0", "--port", "2024"]