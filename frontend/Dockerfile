FROM nginx:alpine

# Statik web dosyalarını Nginx'in yayın dizinine kopyala
COPY index.html /usr/share/nginx/html/index.html
COPY script.js /usr/share/nginx/html/script.js

# Özel Nginx yapılandırmasını kopyala
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]