import { useEffect, useRef, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { runApi } from '../api/run';
import { ApiError } from '../types/api';
import { useQuotaStore } from '../stores/quotaStore';
import { TERMINAL_STATUSES } from '../constants/sync';

/** 默认 2s 轮询；遇 429 指数退避到 20s；终端状态即停 */
export const useRunPolling = (pipelineId?: string, limit = 30) => {
  const [interval, setInterval] = useState(2000);
  const setQuota = useQuotaStore((state) => state.set);
  const setBackingOff = useQuotaStore((state) => state.setBackingOff);
  const errorRef = useRef<unknown>(null);

  const query = useQuery({
    queryKey: ['runs', pipelineId ?? 'all', limit],
    queryFn: () => runApi.list({ pipeline_id: pipelineId, limit }),
    refetchInterval: (queryResult) => {
      const data = queryResult.state.data;
      if (queryResult.state.error instanceof ApiError && queryResult.state.error.status === 429) {
        return Math.min(interval * 2, 20000);
      }
      if (!data) return interval;
      const active = data.items.some((run) => !TERMINAL_STATUSES.includes(run.status));
      return active ? interval : false;
    },
    refetchOnWindowFocus: false,
  });

  useEffect(() => {
    if (query.data?.quota) setQuota(query.data.quota);
  }, [query.data?.quota, setQuota]);

  useEffect(() => {
    errorRef.current = query.error;
    if (query.error instanceof ApiError && query.error.status === 429) {
      setBackingOff(true);
      setInterval((current) => Math.min(current * 2, 20000));
    } else {
      setBackingOff(false);
      setInterval(2000);
    }
  }, [query.error, setBackingOff]);

  return query;
};
