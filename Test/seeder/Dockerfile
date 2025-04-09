FROM python:3.10-slim
WORKDIR /app
COPY . .
RUN pip install flask requests
CMD ["python3", "peer_seeder.py"]
