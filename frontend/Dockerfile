# Multi-stage — React frontend
# Build from repo root: docker build -f frontend/Dockerfile .
FROM node:20-alpine AS build

WORKDIR /app
COPY frontend/package.json ./
RUN npm install
COPY frontend/ ./
ARG VITE_API_URL=http://localhost:8000
ARG VITE_WS_URL=ws://localhost:8000
ENV VITE_API_URL=$VITE_API_URL \
    VITE_WS_URL=$VITE_WS_URL
RUN npm run build

FROM nginx:1.27-alpine AS runtime
COPY --from=build /app/dist /usr/share/nginx/html
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD wget -qO- http://127.0.0.1/ || exit 1
CMD ["nginx", "-g", "daemon off;"]
