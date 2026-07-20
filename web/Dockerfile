# Production image for the Titanic Survivors web SPA.
FROM node:20-slim

WORKDIR /app

# Copy only the manifest + lockfile first so the install layer stays
# cached across source-only changes.
COPY package.json package-lock.json* ./

# Install dependencies. No package-lock.json is committed to the repo
# (all deps in package.json are pinned to "*"), so `npm ci` -- which
# requires an existing, in-sync lockfile -- fails the image build.
# `npm install` resolves and installs from package.json directly,
# generating a lockfile inside the image as a byproduct.
RUN npm install --no-audit --no-fund \
    && which node \
    && which npm

# Copy the remaining project source.
COPY . .

ENV NODE_ENV=production

EXPOSE 4173

# Placeholder command: the framework's production preview server. Not
# executed as part of this setup task.
CMD ["npm", "run", "preview", "--", "--host", "0.0.0.0", "--port", "4173"]
