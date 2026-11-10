import { create } from 'zustand';

interface QuotaState {
  max: number;
  active: number;
  remaining: number;
  backingOff: boolean;
  set: (quota: { max: number; active: number; remaining: number }) => void;
  setBackingOff: (value: boolean) => void;
}

export const useQuotaStore = create<QuotaState>((set) => ({
  max: 2,
  active: 0,
  remaining: 2,
  backingOff: false,
  set: (quota) => set({ max: quota.max, active: quota.active, remaining: quota.remaining }),
  setBackingOff: (value) => set({ backingOff: value }),
}));
