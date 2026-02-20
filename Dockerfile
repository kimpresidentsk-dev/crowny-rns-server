FROM python:3.12-slim
WORKDIR /app
COPY . .
EXPOSE 8080
CMD ["python3", "hanseon.py", "서버.hsn"]
