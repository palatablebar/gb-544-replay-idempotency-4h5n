import { create } from 'zustand';
import type { RunStatus } from '../types/models';

interface RunState {
  statusFilter: RunStatus | 'all';
  pipelineFilter: string | 'all';
  selectedRunId: string | null;
  setStatusFilter: (status: RunStatus | 'all') => void;
  setPipelineFilter: (id: string | 'all') => void;
  select: (id: string | null) => void;
}

export const useRunStore = create<RunState>((set) => ({
  statusFilter: 'all',
  pipelineFilter: 'all',
  selectedRunId: null,
  setStatusFilter: (status) => set({ statusFilter: status }),
  setPipelineFilter: (id) => set({ pipelineFilter: id }),
  select: (id) => set({ selectedRunId: id }),
}));
