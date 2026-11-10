import { create } from 'zustand';

interface SourceState {
  selectedSourceId: string | null;
  probeResult: Record<string, unknown> | null;
  probingId: string | null;
  select: (id: string | null) => void;
  setProbing: (id: string | null) => void;
  setProbeResult: (result: Record<string, unknown> | null) => void;
}

export const useSourceStore = create<SourceState>((set) => ({
  selectedSourceId: null,
  probeResult: null,
  probingId: null,
  select: (id) => set({ selectedSourceId: id }),
  setProbing: (id) => set({ probingId: id }),
  setProbeResult: (result) => set({ probeResult: result }),
}));
