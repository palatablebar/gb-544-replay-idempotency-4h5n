import { cronText } from '../../utils/cronText';

interface Props {
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
}

export const CronField = ({ value, onChange, disabled }: Props) => {
  const valid = value.trim().split(/\s+/).length === 5;
  return (
    <div className="flex flex-col gap-1">
      <label className="label-caps">调度 cron</label>
      <div className="flex items-center gap-2">
        <input
          className="num w-[140px]"
          value={value}
          disabled={disabled}
          placeholder="0 2 * * *"
          onChange={(event) => onChange(event.target.value)}
        />
        <span className="text-dense" style={{ color: valid ? 'var(--color-dim)' : 'var(--color-danger)' }}>
          {valid ? cronText(value) : '需要 5 段表达式'}
        </span>
      </div>
    </div>
  );
};
