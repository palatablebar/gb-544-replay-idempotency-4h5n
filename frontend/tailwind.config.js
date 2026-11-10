/** Tailwind 主题：全部映射到 tokens.css 的 oklch 语义 token。 */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        rail: 'var(--color-rail)',
        deck: 'var(--color-deck)',
        panel: 'var(--color-panel)',
        select: 'var(--color-select)',
        ink: 'var(--color-ink)',
        dim: 'var(--color-dim)',
        wire: 'var(--color-wire)',
        signal: 'var(--color-signal)',
        warn: 'var(--color-warn)',
        danger: 'var(--color-danger)',
        ok: 'var(--color-ok)',
      },
      fontFamily: {
        display: ['Syne', 'Noto Sans SC', 'PingFang SC', 'sans-serif'],
        body: ['Karla', 'Noto Sans SC', 'PingFang SC', 'sans-serif'],
      },
      fontSize: {
        micro: ['11px', '16px'],
        dense: ['13px', '20px'],
        base: ['14px', '22px'],
        lead: ['clamp(16px, 1.4vw, 19px)', '26px'],
        title: ['clamp(20px, 2vw, 27px)', '34px'],
      },
    },
  },
  plugins: [],
};
