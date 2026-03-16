const CACHE_NAME = 'asphaleia-phase3-v1';
const urlsToCache = [
  '/',
  '/index.html',
  '/manifest.json',
  // Leaflet CDN (critical for map)
  'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css',
  'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js',
  // OpenStreetMap tiles (basic caching)
  'https://a.tile.openstreetmap.org/14/16384/8192.png',
  'https://b.tile.openstreetmap.org/14/16384/8192.png', 
  'https://c.tile.openstreetmap.org/14/16384/8192.png'
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
  
  // Leaflet tiles: Cache-first (fast map)
  if (event.request.url.includes('tile.openstreetmap.org')) {
    event.respondWith(
      caches.match(event.request).then(response => {
        return response || fetch(event.request).then(fetchResponse => {
          caches.open(CACHE_NAME).then(cache => {
            cache.put(event.request, fetchResponse.clone());
          });
          return fetchResponse;
        });
      }).catch(() => {
        return caches.match('/index.html');
      })
    );
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
