// static/sw.js (or serve from root)
const CACHE_NAME = 'oxsmart-v1';
const OFFLINE_PAGE = '/offline.html'; // create this template

// List all routes you want available offline
const PRECACHE_URLS = [
  '/',
  '/dashboard',
  '/products',
  '/products/screens',
  '/sales',
  '/sales/screens',
  '/purchases',
  '/purchases/screens',
  '/analytics',
  '/today-sales',
  '/today-sales/screens',
  '/archive',
  '/inventory/import',
  '/admin/users',
  '/login',
  '/signup',
  '/static/css/style.css',
  '/static/js/offline.js',
  '/static/js/main.js',
  // add any other static assets (e.g., fonts, images)
];

// Install event: pre‑cache all important pages
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(PRECACHE_URLS))
      .then(() => self.skipWaiting())
  );
});

// Activate event: clean up old caches
self.addEventListener('activate', event => {
  const cacheWhitelist = [CACHE_NAME];
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cacheName => {
          if (cacheWhitelist.indexOf(cacheName) === -1) {
            return caches.delete(cacheName);
          }
        })
      );
    }).then(() => self.clients.claim())
  );
});

// Fetch event: serve from cache if available, else network, else fallback
self.addEventListener('fetch', event => {
  const request = event.request;
  const url = new URL(request.url);

  // Skip non‑GET requests and external resources (e.g., analytics, images from CDN)
  if (request.method !== 'GET' || url.origin !== location.origin) {
    return;
  }

  event.respondWith(
    caches.match(request)
      .then(cachedResponse => {
        if (cachedResponse) {
          // Return cached version, but update it in background (stale‑while‑revalidate)
          event.waitUntil(
            fetch(request).then(networkResponse => {
              return caches.open(CACHE_NAME).then(cache => {
                cache.put(request, networkResponse.clone());
                return networkResponse;
              });
            }).catch(() => {})
          );
          return cachedResponse;
        }

        // Not in cache – try network, fallback to offline page
        return fetch(request)
          .then(networkResponse => {
            // Cache a copy for next time
            const responseClone = networkResponse.clone();
            caches.open(CACHE_NAME).then(cache => cache.put(request, responseClone));
            return networkResponse;
          })
          .catch(() => {
            // If the request is for a page (HTML), serve the offline fallback
            if (request.headers.get('accept').includes('text/html')) {
              return caches.match(OFFLINE_PAGE);
            }
            // For other assets, return a simple error response
            return new Response('Offline', { status: 503, statusText: 'Service Unavailable' });
          });
      })
  );
});