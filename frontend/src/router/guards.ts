import { redirect } from 'react-router-dom';
import { tokenStore } from '../api/client';
import type { Role } from '../types/models';

export const requireAuth = () => {
  if (!tokenStore.get()) return redirect('/login');
  return null;
};

export const roleHome = (role: Role | undefined): string => {
  if (role === 'viewer') return '/targets';
  return '/sources';
};

export const canOpenMapping = (role: Role | undefined): boolean =>
  role === 'owner' || role === 'operator';

export const guardMapping = (role: Role | undefined): string | null => {
  if (!role) return '/login';
  if (!canOpenMapping(role)) return '/targets';
  return null;
};
