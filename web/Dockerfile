# Production image for the Titanic Survivors web SPA.
FROM node:20-slim

WORKDIR /app

# Copy only the manifest + lockfile first so the install layer stays
# cached across source-only changes.
COPY package.json package-lock.json* ./

# Non-interactive, frozen install.
RUN npm ci --no-audit --no-fund \
    && which node \
    && which npm

# Copy the remaining project source.
COPY . .

ENV NODE_ENV=production

EXPOSE 4173

# Placeholder command: the framework's production preview server. Not
# executed as part of this setup task.
CMD ["npm", "run", "preview", "--", "--host", "0.0.0.0", "--port", "4173"]
