import type { SyncPipeline } from '../../types/models';
import { SourceBadge } from '../common/SourceBadge';
import { RunStatusPill } from '../common/RunStatusPill';
import { cronText } from '../../utils/cronText';

interface Props {
  pipelines: SyncPipeline[];
  selectedId: string | null;
  collapsedSources: string[];
  onSelect: (id: string) => void;
  onToggleSource: (sourceId: string) => void;
}

/** 左侧 220px 管道树：按源分组，组间走线；与运行流之间是 1px 走线而不是卡片边框 */
export const PipelineTree = ({ pipelines, selectedId, collapsedSources, onSelect, onToggleSource }: Props) => {
  const groups = new Map<string, { name: string; type: SyncPipeline['source_type']; status: SyncPipeline['source_status']; items: SyncPipeline[] }>();
  for (const pipeline of pipelines) {
    const key = pipeline.source_id;
    if (!groups.has(key)) {
      groups.set(key, {
        name: pipeline.source_name ?? '未命名源',
        type: pipeline.source_type,
        status: pipeline.source_status,
        items: [],
      });
    }
    groups.get(key)!.items.push(pipeline);
  }

  return (
    <aside className="w-[220px] shrink-0 overflow-y-auto border-r" style={{ borderColor: 'var(--color-wire)' }}>
      <div className="label-caps px-3 py-2">管道树 · {pipelines.length}</div>
      {Array.from(groups.entries()).map(([sourceId, group]) => {
        const collapsed = collapsedSources.includes(sourceId);
        return (
          <div key={sourceId} className="hairline">
            <button
              className="flex w-full items-center gap-2 px-3 py-2 text-left hover:bg-deck"
              onClick={() => onToggleSource(sourceId)}
            >
              <span className="text-micro text-dim">{collapsed ? '+' : '−'}</span>
              <SourceBadge type={(group.type ?? 'csv') as never} status={(group.status ?? 'untested') as never} name={group.name} />
            </button>
            {!collapsed &&
              group.items.map((pipeline) => (
                <button
                  key={pipeline.id}
                  onClick={() => onSelect(pipeline.id)}
                  className="block w-full border-l-2 px-3 py-1.5 text-left"
                  style={{
                    borderColor: selectedId === pipeline.id ? 'var(--color-signal)' : 'transparent',
                    backgroundColor: selectedId === pipeline.id ? 'var(--color-select)' : 'transparent',
                  }}
                >
                  <div className="truncate text-dense text-ink">{pipeline.name}</div>
                  <div className="num truncate text-micro text-dim">{pipeline.target_full_name}</div>
                  <div className="mt-0.5 flex items-center gap-2">
                    <span className="text-micro text-dim">{pipeline.sync_mode === 'incremental' ? '增量' : '全量'}</span>
                    {pipeline.last_run ? (
                      <RunStatusPill status={pipeline.last_run.status} compact />
                    ) : (
                      <span className="text-micro text-dim">未运行</span>
                    )}
                  </div>
                  <div className="num truncate text-micro text-dim">{cronText(pipeline.schedule_cron)}</div>
                </button>
              ))}
          </div>
        );
      })}
    </aside>
  );
};
