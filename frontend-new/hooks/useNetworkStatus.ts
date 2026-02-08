"use client";

/**
 * useNetworkStatus Hook
 *
 * Monitors browser online/offline state via the Network Information API.
 * Returns a reactive boolean that components can use to show offline UI.
 */

import { useState, useEffect, useSyncExternalStore } from "react";

function subscribe(callback: () => void) {
    window.addEventListener("online", callback);
    window.addEventListener("offline", callback);
    return () => {
        window.removeEventListener("online", callback);
        window.removeEventListener("offline", callback);
    };
}

function getSnapshot() {
    return navigator.onLine;
}

function getServerSnapshot() {
    // Always assume online during SSR
    return true;
}

/**
 * Returns `true` when the browser has network connectivity, `false` when offline.
 *
 * Uses `useSyncExternalStore` for tear-free reads — the standard React 18+
 * pattern for subscribing to external browser APIs.
 */
export function useNetworkStatus(): boolean {
    return useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
}
