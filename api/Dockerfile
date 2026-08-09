FROM public.ecr.aws/awsguru/aws-lambda-adapter:0.9.1 AS adapter
FROM python:3.12-slim
COPY --from=adapter /lambda-adapter /opt/extensions/lambda-adapter
ENV AWS_LWA_INVOKE_MODE=response_stream
ENV PORT=8080
COPY . /app
WORKDIR /app
RUN pip install --no-cache-dir -r requirements.txt
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
