export const formatCount = (value: number | null | undefined): string =>
  value === null || value === undefined ? '0' : value.toLocaleString('en-US');

export const formatTriplet = (read: number, written: number, rejected: number): string =>
  `${formatCount(read)} / ${formatCount(written)} / ${formatCount(rejected)}`;

export const formatDuration = (started: string | null, finished: string | null): string => {
  if (!started) return '—';
  const start = new Date(started).getTime();
  const end = finished ? new Date(finished).getTime() : Date.now();
  const seconds = Math.max(Math.floor((end - start) / 1000), 0);
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ${seconds % 60}s`;
  return `${Math.floor(minutes / 60)}h ${minutes % 60}m`;
};

export const formatTimestamp = (value: string | null): string => {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  const pad = (num: number) => String(num).padStart(2, '0');
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`;
};
