# Front-end do ms-dashboard — build com Vite, servido por nginx
FROM node:20-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
# URL pública do BFF (injetada no build). Vazia => caminhos relativos (local/compose).
ARG VITE_API_BASE_URL=""
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
RUN npm run build

FROM nginx:1.27-alpine
# Template: o entrypoint do nginx roda envsubst e gera o default.conf na partida.
# O filtro garante que apenas PORT e BFF_UPSTREAM sejam substituídos — as variáveis
# de runtime do nginx ($host, $uri, $bff_upstream) são preservadas.
COPY nginx.conf.template /etc/nginx/templates/default.conf.template
COPY --from=build /app/dist /usr/share/nginx/html
# PORT: porta de escuta (Render sobrescreve). BFF_UPSTREAM: host:porta do BFF no
# docker-compose (na nuvem a rota de proxy não é usada).
ENV PORT=80 \
    BFF_UPSTREAM=bff:8006 \
    NGINX_ENVSUBST_FILTER="^(PORT|BFF_UPSTREAM)$"
CMD ["nginx", "-g", "daemon off;"]
