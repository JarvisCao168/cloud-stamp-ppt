FROM node:20-slim

WORKDIR /app

COPY package*.json ./
RUN npm ci --omit=dev 2>/dev/null || npm install --legacy-peer-deps

COPY . .

# Build Next.js app
RUN npm run build

EXPOSE 3000

CMD ["npm", "start"]
