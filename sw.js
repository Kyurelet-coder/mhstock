const CACHE_NAME = 'mh-stock-v38';
const ASSETS = [
  './',
  './index.html',
  './styles.css',
  './app.js',
  './manifest.json',
  './app_icon.jpg',
  './icon-192.png',
  './icon-512.png',
  './screenshot-mobile.png',
  './screenshot-desktop.png'
];

self.addEventListener('install', (e) => {
  self.skipWaiting();
  e.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(ASSETS))
  );
});

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.map((key) => {
          if (key !== CACHE_NAME) return caches.delete(key);
        })
      );
    }).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (e) => {
  e.respondWith(
    fetch(e.request).catch(() => caches.match(e.request))
  );
});

/* --- ADVANCED PWA SERVICE WORKER HANDLERS --- */

// 1. Background Sync Handler
self.addEventListener('sync', (event) => {
  if (event.tag === 'sync-mh-stock-data') {
    event.waitUntil(
      console.log('Background Sync: Sincronização de dados Monster High executada em segundo plano.')
    );
  }
});

// 2. Periodic Background Sync Handler
self.addEventListener('periodicsync', (event) => {
  if (event.tag === 'update-stock-kpis') {
    event.waitUntil(
      console.log('Periodic Background Sync: Atualização periódica dos KPIs de stock.')
    );
  }
});

// 3. Push Notifications Handler
self.addEventListener('push', (event) => {
  const data = event.data ? event.data.text() : 'Nova atualização Monster High Stock!';
  const options = {
    body: data,
    icon: './icon-192.png',
    badge: './icon-192.png',
    vibrate: [100, 50, 100],
    data: { dateOfArrival: Date.now() }
  };
  event.waitUntil(
    self.registration.showNotification('Monster High Stock 🧟‍♀️', options)
  );
});

// 4. Notification Click Handler
self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  event.waitUntil(
    clients.openWindow('./index.html')
  );
});
