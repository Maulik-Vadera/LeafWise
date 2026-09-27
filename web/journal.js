const DB = 'leafwise-journal-v1';
let opened;
function database() {
  if (!opened) opened = new Promise((resolve, reject) => {
    const request = indexedDB.open(DB, 1);
    request.onupgradeneeded = () => request.result.createObjectStore('scans', {keyPath:'id'});
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(new Error('Browser storage is unavailable. You can still download this report.'));
  });
  return opened;
}
async function transaction(mode, perform) {
  const db = await database();
  return new Promise((resolve, reject) => {
    const tx = db.transaction('scans', mode);
    const request = perform(tx.objectStore('scans'));
    let result;
    request.onsuccess = () => { result = request.result; };
    tx.oncomplete = () => resolve(result);
    tx.onerror = tx.onabort = () => reject(new Error('Your browser could not save this. Download the report instead.'));
  });
}
export async function listScans() { return (await transaction('readonly', store => store.getAll())).sort((a,b) => b.created_at.localeCompare(a.created_at)); }
export async function saveScan(scan) {
  const records = await listScans();
  if (records.length >= 50 && !records.some(s => s.id === scan.id)) throw new Error('Your journal has 50 scans. Export it and remove an older scan to make room.');
  return transaction('readwrite', store => store.put(scan));
}
export const removeScan = id => transaction('readwrite', store => store.delete(id));
