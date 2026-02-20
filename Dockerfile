FROM python:3.12-slim
ENV LANG=C.UTF-8
ENV PYTHONIOENCODING=utf-8
WORKDIR /app
COPY . .
RUN ls -la *.hsn *.py
EXPOSE 8080
CMD ["python3", "start.py"]
