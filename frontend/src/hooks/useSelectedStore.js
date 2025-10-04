// Simple localStorage-backed selected tracks store
import { useEffect, useState, useCallback } from "react";

const LS_KEY = "selected_tracks";

function load() {
  try { return JSON.parse(localStorage.getItem(LS_KEY) || "[]"); } catch { return []; }
}

function save(list) {
  localStorage.setItem(LS_KEY, JSON.stringify(list));
}

export default function useSelectedStore() {
  const [selected, setSelected] = useState(load);

  useEffect(() => { save(selected); }, [selected]);

  const addSelected = useCallback((track) => {
    if (!track || !track.id) return;
    setSelected(prev => {
      const seen = new Set();
      const out = [];
      // newest first
      const next = [track, ...prev];
      for (const t of next) {
        const id = t && t.id;
        if (id && !seen.has(id)) { seen.add(id); out.push(t); }
      }
      return out;
    });
  }, []);

  const removeSelected = useCallback((id) => {
    setSelected(prev => prev.filter(t => t && t.id !== id));
  }, []);

  const clearSelected = useCallback(() => setSelected([]), []);

  return { selected, addSelected, removeSelected, clearSelected };
}

