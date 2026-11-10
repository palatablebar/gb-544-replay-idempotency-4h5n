import { useMutation, useQueryClient } from '@tanstack/react-query';
import { sourceApi } from '../api/source';
import { useSourceStore } from '../stores/sourceStore';

export const useSourceProbe = () => {
  const queryClient = useQueryClient();
  const setProbing = useSourceStore((state) => state.setProbing);
  const setProbeResult = useSourceStore((state) => state.setProbeResult);

  const mutation = useMutation({
    mutationFn: async (id: string) => {
      setProbing(id);
      return sourceApi.probe(id);
    },
    onSuccess: (data) => {
      setProbeResult(data.probe);
      queryClient.invalidateQueries({ queryKey: ['sources'] });
    },
    onSettled: () => setProbing(null),
  });

  return mutation;
};
