FROM node:22-slim

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

EXPOSE 3000

# `next dev` (not a production build): this Dockerfile targets local
# development experience (this Sprint's own goal) -- hot reload via the
# ./frontend/src bind mount in docker-compose.yml, same pattern as the
# backend's own ./src:/app/src:ro mount. --hostname 0.0.0.0 is required
# inside a container; without it Next's dev server only binds to
# 127.0.0.1 inside the container's own network namespace, unreachable
# through the published port.
CMD ["npm", "run", "dev", "--", "--hostname", "0.0.0.0"]
