import { create } from 'zustand';

interface PipelineState {
  selectedPipelineId: string | null;
  collapsedSources: string[];
  select: (id: string | null) => void;
  toggleSource: (sourceId: string) => void;
}

export const usePipelineStore = create<PipelineState>((set) => ({
  selectedPipelineId: null,
  collapsedSources: [],
  select: (id) => set({ selectedPipelineId: id }),
  toggleSource: (sourceId) =>
    set((state) => ({
      collapsedSources: state.collapsedSources.includes(sourceId)
        ? state.collapsedSources.filter((id) => id !== sourceId)
        : [...state.collapsedSources, sourceId],
    })),
}));
