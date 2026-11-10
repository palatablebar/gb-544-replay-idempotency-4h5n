import { create } from 'zustand';
import type { FieldMapping, PreviewResult } from '../types/models';

interface MappingState {
  dirty: boolean;
  preview: PreviewResult | null;
  draft: FieldMapping[];
  setDraft: (draft: FieldMapping[]) => void;
  markDirty: (dirty: boolean) => void;
  setPreview: (preview: PreviewResult | null) => void;
  reset: () => void;
}

export const useMappingStore = create<MappingState>((set) => ({
  dirty: false,
  preview: null,
  draft: [],
  setDraft: (draft) => set({ draft }),
  markDirty: (dirty) => set({ dirty }),
  setPreview: (preview) => set({ preview }),
  reset: () => set({ dirty: false, preview: null, draft: [] }),
}));
