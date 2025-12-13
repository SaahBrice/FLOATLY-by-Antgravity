/**
 * Floatly Service Worker
 * Enables offline functionality, caching, and push notifications for the PWA
 */

const CACHE_NAME = 'floatly-v1.0.1';

// Assets to cache on install (only essential existing files)
const ASSETS_TO_CACHE = [
    '/',
];

// Install event - cache essential assets
self.addEventListener('install', (event) => {
    console.log('[ServiceWorker] Installing...');

    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(async (cache) => {
                console.log('[ServiceWorker] Caching app shell');
                // Cache each item individually to avoid failing on one bad URL
                for (const url of ASSETS_TO_CACHE) {
                    try {
                        await cache.add(url);
                    } catch (e) {
                        console.warn('[ServiceWorker] Failed to cache:', url);
                    }
                }
            })
    );

    // Activate immediately
    self.skipWaiting();
});

// Activate event - clean up old caches
self.addEventListener('activate', (event) => {
    console.log('[ServiceWorker] Activating...');

    event.waitUntil(
        caches.keys().then((cacheNames) => {
            return Promise.all(
                cacheNames.map((cacheName) => {
                    if (cacheName !== CACHE_NAME) {
                        console.log('[ServiceWorker] Deleting old cache:', cacheName);
                        return caches.delete(cacheName);
                    }
                })
            );
        })
    );

    // Take control of all pages immediately
    self.clients.claim();
});

// Fetch event - serve from cache, fall back to network
self.addEventListener('fetch', (event) => {
    // Skip non-GET requests
    if (event.request.method !== 'GET') {
        return;
    }

    // Skip cross-origin requests
    if (!event.request.url.startsWith(self.location.origin)) {
        return;
    }

    event.respondWith(
        caches.match(event.request)
            .then((cachedResponse) => {
                if (cachedResponse) {
                    // Return cached response
                    return cachedResponse;
                }

                // Fetch from network
                return fetch(event.request)
                    .then((response) => {
                        // Check if valid response
                        if (!response || response.status !== 200 || response.type !== 'basic') {
                            return response;
                        }

                        // Clone response for caching
                        const responseToCache = response.clone();

                        caches.open(CACHE_NAME)
                            .then((cache) => {
                                cache.put(event.request, responseToCache);
                            });

                        return response;
                    })
                    .catch(() => {
                        // Network failed, try to serve offline page for navigation requests
                        if (event.request.mode === 'navigate') {
                            return caches.match(OFFLINE_URL);
                        }
                    });
            })
    );
});

// Background sync for offline transactions
self.addEventListener('sync', (event) => {
    console.log('[ServiceWorker] Sync event:', event.tag);

    if (event.tag === 'sync-transactions') {
        event.waitUntil(syncTransactions());
    }
});

// Sync pending transactions when back online
async function syncTransactions() {
    try {
        // Get pending transactions from IndexedDB
        const pendingTransactions = await getPendingTransactions();

        for (const transaction of pendingTransactions) {
            await fetch('/api/transactions/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(transaction),
            });

            // Remove from pending after successful sync
            await removePendingTransaction(transaction.id);
        }

        console.log('[ServiceWorker] Transactions synced successfully');
    } catch (error) {
        console.error('[ServiceWorker] Sync failed:', error);
    }
}

// Push notification handler
self.addEventListener('push', (event) => {
    console.log('[ServiceWorker] Push received');

    let notification = {
        title: 'Floatly',
        body: 'You have a new notification',
        icon: '/static/images/icon-192x192.png',
        badge: '/static/images/badge-72x72.png',
        tag: 'floatly-notification',
        data: {},
    };

    if (event.data) {
        try {
            const data = event.data.json();
            notification = { ...notification, ...data };
        } catch (e) {
            notification.body = event.data.text();
        }
    }

    event.waitUntil(
        self.registration.showNotification(notification.title, {
            body: notification.body,
            icon: notification.icon,
            badge: notification.badge,
            tag: notification.tag,
            data: notification.data,
            vibrate: [100, 50, 100],
            actions: notification.actions || [],
        })
    );
});

// Notification click handler
self.addEventListener('notificationclick', (event) => {
    console.log('[ServiceWorker] Notification clicked');

    event.notification.close();

    const urlToOpen = event.notification.data?.url || '/dashboard/';

    event.waitUntil(
        clients.matchAll({ type: 'window', includeUncontrolled: false })
            .then((clientList) => {
                // If a controlled window is already open, focus it
                for (const client of clientList) {
                    if ('focus' in client) {
                        return client.focus().then(() => {
                            if ('navigate' in client) {
                                return client.navigate(urlToOpen);
                            }
                        });
                    }
                }
                // Otherwise, open a new window
                if (clients.openWindow) {
                    return clients.openWindow(urlToOpen);
                }
            })
            .catch((err) => {
                console.warn('[ServiceWorker] Click handling error:', err);
                // Fallback: just open new window
                if (clients.openWindow) {
                    return clients.openWindow(urlToOpen);
                }
            })
    );
});

// Placeholder functions for IndexedDB operations
// These will be implemented when we build the offline-first features
function getPendingTransactions() {
    return Promise.resolve([]);
}

function removePendingTransaction(id) {
    return Promise.resolve();
}
