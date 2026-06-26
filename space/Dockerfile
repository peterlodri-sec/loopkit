FROM python:3.11-slim
WORKDIR /app
COPY space/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV HEADROOM_EVAL_STATE=/data/eval_state
RUN mkdir -p /data/eval_state
EXPOSE 7860
CMD ["python", "space/app.py"]
