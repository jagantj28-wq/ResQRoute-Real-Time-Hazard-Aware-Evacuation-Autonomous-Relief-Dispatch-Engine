const CACHE_NAME = "resqroute-citizen-v1";
const ASSETS_TO_CACHE = [
  "/",
  "/citizen",
  "/shared/css/styles.css",
  "/shared/js/socket.js",
  "/citizen-static/app.js",
  "/api/routing/shelters"
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      console.log("[ResQRoute SW] Caching offline emergency assets...");
      return cache.addAll(ASSETS_TO_CACHE).catch((err) => console.warn("Caching error:", err));
    })
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.map((k) => {
          if (k !== CACHE_NAME) {
            return caches.delete(k);
          }
        })
      );
    })
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  event.respondWith(
    caches.match(event.request).then((cachedResponse) => {
      if (cachedResponse) {
        return cachedResponse;
      }
      return fetch(event.request).catch(() => {
        // Fallback for shelters endpoint
        if (event.request.url.includes("/api/routing/shelters")) {
          return caches.match("/api/routing/shelters");
        }
      });
    })
  );
});
