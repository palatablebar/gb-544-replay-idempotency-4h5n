import { api } from './client';
import type { User } from '../types/models';

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

export const authApi = {
  login: (email: string, password: string) =>
    api.postAnonymous<LoginResponse>('/auth/login', { email, password }),
  me: () => api.get<User>('/auth/me'),
  refresh: (refresh_token: string) => api.post<{ access_token: string }>('/auth/refresh', { refresh_token }),
};
