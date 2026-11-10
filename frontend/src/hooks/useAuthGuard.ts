import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { tokenStore } from '../api/client';
import { useAuthStore } from '../stores/authStore';

export const useAuthGuard = () => {
  const navigate = useNavigate();
  const user = useAuthStore((state) => state.user);
  const loadMe = useAuthStore((state) => state.loadMe);

  useEffect(() => {
    if (!user && tokenStore.get()) {
      void loadMe();
    }
  }, [user, loadMe]);

  useEffect(() => {
    if (!tokenStore.get()) navigate('/login', { replace: true });
  }, [navigate]);

  return { user, ready: Boolean(user) || Boolean(tokenStore.get()) };
};
