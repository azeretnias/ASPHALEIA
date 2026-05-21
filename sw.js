const CACHE_NAME = 'asphaleia-phase3-v2';
const urlsToCache = [
  '/',
  '/index.html',
  '/manifest.json'
];

// Install: Cache core assets
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(urlsToCache))
      .then(() => self.skipWaiting())
  );
});

// Activate: Clean old caches
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cacheName => {
          if (cacheName !== CACHE_NAME) {
            return caches.delete(cacheName);
          }
        })
      );
    }).then(() => self.clients.claim())
  );
});

// Fetch: Network-first → Cache → Offline page
self.addEventListener('fetch', event => {
  // HTML: Network-first (always fresh)
  if (event.request.destination === 'document') {
    event.respondWith(
      fetch(event.request).catch(() => 
        caches.match('/index.html')
      )
    );
    return;
  }
  
  // Leaflet tiles: do not cache OSM tiles in the service worker.
  if (event.request.url.includes('tile.openstreetmap.org')) {
    event.respondWith(fetch(event.request));
    return;
  }
  
  // Everything else: Cache-first
  event.respondWith(
    caches.match(event.request).then(response => {
      return response || fetch(event.request).catch(() => {
        return caches.match('/index.html');
      });
    })
  );
});
