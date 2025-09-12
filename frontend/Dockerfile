# Stage 1: Build the React application
FROM node:18-alpine AS build

WORKDIR /app

COPY package.json package-lock.json* ./

RUN npm install

COPY . .

RUN npm run build

# Stage 2: Serve the application with Nginx
FROM nginx:1.21-alpine

COPY --from=build /app/dist /usr/share/nginx/html

# When the nginx default page is requested, serve index.html
RUN echo "server { 
  listen 80; 
  location / { 
    root /usr/share/nginx/html; 
    index index.html; 
    try_files $uri $uri/ /index.html; 
  }
}" > /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
