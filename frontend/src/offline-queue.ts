/**
 * MetaLex Offline Inspection Queue
 * Stores inspection requests in IndexedDB when offline and auto-syncs when online.
 */

const DB_NAME = 'metalex_offline_db';
const STORE_NAME = 'queued_inspections';
const DB_VERSION = 1;

export interface QueuedInspection {
  id: string;
  timestamp: number;
  files: { name: string; type: string; base64: string }[];
  latitude?: number;
  longitude?: number;
  status: 'PENDING' | 'SYNCING' | 'SYNCED' | 'FAILED';
  error?: string;
}

function openDB(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);

    request.onupgradeneeded = (event) => {
      const db = (event.target as IDBOpenDBRequest).result;
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        db.createObjectStore(STORE_NAME, { keyPath: 'id' });
      }
    };

    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

export async function queueOfflineInspection(
  files: File[],
  coords?: { latitude?: number; longitude?: number }
): Promise<string> {
  const db = await openDB();
  const id = `OFFLINE-${Date.now()}-${Math.random().toString(36).substr(2, 6).toUpperCase()}`;

  const convertedFiles = await Promise.all(
    files.map(async (f) => {
      const base64 = await fileToBase64(f);
      return { name: f.name, type: f.type, base64 };
    })
  );

  const record: QueuedInspection = {
    id,
    timestamp: Date.now(),
    files: convertedFiles,
    latitude: coords?.latitude,
    longitude: coords?.longitude,
    status: 'PENDING'
  };

  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, 'readwrite');
    const store = tx.objectStore(STORE_NAME);
    const req = store.add(record);
    req.onsuccess = () => resolve(id);
    req.onerror = () => reject(req.error);
  });
}

export async function getQueuedInspections(): Promise<QueuedInspection[]> {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, 'readonly');
    const store = tx.objectStore(STORE_NAME);
    const req = store.getAll();
    req.onsuccess = () => resolve(req.result || []);
    req.onerror = () => reject(req.error);
  });
}

export async function removeQueuedInspection(id: string): Promise<void> {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, 'readwrite');
    const store = tx.objectStore(STORE_NAME);
    const req = store.delete(id);
    req.onsuccess = () => resolve();
    req.onerror = () => reject(req.error);
  });
}

export async function getOfflineCount(): Promise<number> {
  try {
    const list = await getQueuedInspections();
    return list.filter((i) => i.status === 'PENDING').length;
  } catch (e) {
    return 0;
  }
}

function fileToBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.readAsDataURL(file);
    reader.onload = () => resolve(reader.result as string);
    reader.onerror = (error) => reject(error);
  });
}
