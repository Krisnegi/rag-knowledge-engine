# Stage 1: Build the app
FROM node:18-slim AS builder

WORKDIR /app

# 1. Install OpenSSL so Prisma can generate the client
RUN apt-get update -y && apt-get install -y openssl

COPY package*.json ./
COPY prisma ./prisma/
RUN npm install
RUN npx prisma generate
COPY . .
RUN npm run build

# Stage 2: Run the app
FROM node:18-slim

WORKDIR /app

# 2. Install OpenSSL so the server can talk to Postgres
RUN apt-get update -y && apt-get install -y openssl

COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package*.json ./
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/prisma ./prisma

EXPOSE 3000

# Start the server and run migrations automatically
CMD npx prisma migrate deploy && node dist/main