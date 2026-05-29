const CACHE_NAME = 'mv-stend-v1';
const STATIC_ASSETS = [
  '/',
  '/static/css/style.css',
  '/static/css/monitoring.css',
  '/static/fonts/inter.css',
  '/static/js/common.js',
  '/static/js/auth.js',
  '/static/js/connection_monitor.js',
  '/static/js/sidebar.js',
  '/static/js/theme.js',
  '/static/js/toast.js',
  '/static/js/websocket.js',
  '/static/js/monitoring.js',
  '/static/js/vendor/socket.io.min.js',
  '/static/manifest.json',
  '/static/icons/icon-72x72.svg',
  '/static/icons/icon-192x192.svg',
  '/static/icons/icon-512x512.svg'
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => cache.addAll(STATIC_ASSETS))
  );
  self.skipWaiting();
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', event => {
  const { request } = event;
  const url = new URL(request.url);

  if (request.method !== 'GET') return;

  // API — network first, cache fallback
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(
      fetch(request)
        .then(response => {
          const clone = response.clone();
          caches.open(CACHE_NAME).then(cache => cache.put(request, clone));
          return response;
        })
        .catch(() => caches.match(request))
    );
    return;
  }

  // Static — cache first, network fallback
  event.respondWith(
    caches.match(request).then(cached => {
      if (cached) return cached;
      return fetch(request).then(response => {
        if (response.ok && request.url.startsWith('http')) {
          const clone = response.clone();
          caches.open(CACHE_NAME).then(cache => cache.put(request, clone));
        }
        return response;
      });
    })
  );
});
