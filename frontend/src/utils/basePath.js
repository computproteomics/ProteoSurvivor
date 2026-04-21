function normalizeBasePath(value) {
  if (!value || value === '/') {
    return '/';
  }

  const withLeadingSlash = value.startsWith('/') ? value : `/${value}`;
  return withLeadingSlash.replace(/\/+$/, '') || '/';
}

export const routerBaseName = normalizeBasePath(import.meta.env.BASE_URL);

export function withBasePath(path) {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  return routerBaseName === '/' ? normalizedPath : `${routerBaseName}${normalizedPath}`;
}
