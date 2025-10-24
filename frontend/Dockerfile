# syntax=docker/dockerfile:1.7

FROM node:20-alpine AS base
WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm install --frozen-lockfile
COPY . .

ARG VITE_API_BASE=/api
ARG VITE_BACKEND_ORIGIN=http://localhost:8000
ENV VITE_API_BASE=$VITE_API_BASE \
    VITE_BACKEND_ORIGIN=$VITE_BACKEND_ORIGIN

RUN npm run build

FROM nginx:1.27-alpine AS runtime

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=base /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
