# Built from the REPOSITORY ROOT as context (not backend/), so the content/
# knowledge base — which lives outside backend/ — can be baked into the image.
# Render's free Docker runtime has no repo volume mounts: the image is the whole
# deploy, so the content must ship inside it.
#
#   docker build -f backend/Dockerfile -t ask-me-backend .
#
FROM python:3.12-slim
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./
COPY content/ ./content/
ENV CONTENT_DIR=./content
EXPOSE 8000
# Render/most hosts inject $PORT; the dockerCommand in render.yaml binds it.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
