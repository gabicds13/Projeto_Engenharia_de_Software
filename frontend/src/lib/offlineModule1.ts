// Acesso local de desenvolvimento: o frontend continua usando fetch para o BFF.
export const MODULE1_OFFLINE =
  import.meta.env.VITE_MODULE1_OFFLINE === "true" &&
  (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1");
