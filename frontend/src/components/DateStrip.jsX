import { useMemo } from 'react';

const toDayKey = (dateStr) => {
  if (!dateStr) return null;
  const d = new Date(dateStr);
  return isNaN(d.getTime()) ? null : d.toISOString().split('T')[0];
};

export function DateStrip({ reports, selectedDate, onSelectDate }) {
  const availableDates = useMemo(() => {
    const days = new Set(reports.map((r) => toDayKey(r.report_date)).filter(Boolean));
    return [...days].sort((a, b) => new Date(b) - new Date(a));
  }, [reports]);

  const todayKey = toDayKey(new Date().toISOString());
  const chipClass = (isSelected) =>
    `shrink-0 px-3.5 py-1.5 rounded-md text-xs font-semibold border transition-colors ${
      isSelected
        ? 'bg-[var(--accent-dark)] text-white border-[var(--accent-dark)]'
        : 'bg-white text-[var(--ink-soft)] border-[var(--border)] hover:border-[var(--accent)]'
    }`;

  return (
    <div className="flex gap-2 overflow-x-auto pb-2 mb-4">
      <button onClick={() => onSelectDate(null)} className={chipClass(selectedDate === null)}>
        All dates
      </button>
      {availableDates.map((day) => (
        <button key={day} onClick={() => onSelectDate(day)} className={chipClass(selectedDate === day)}>
          {day === todayKey ? 'Today' : new Date(day).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' })}
        </button>
      ))}
    </div>
  );
}

export { toDayKey };