export interface BarItem {
  label: string;
  value: number;
  color: string;
  displayValue?: string;
  displayLabel?: string;
}

interface Props {
  items: BarItem[];
  maxValue?: number;
  onItemClick?: (label: string) => void;
  activeLabel?: string | null;
}

export function BarList({ items, maxValue, onItemClick, activeLabel }: Props) {
  const max = maxValue ?? Math.max(...items.map((i) => i.value), 1);
  return (
    <div className="barlist">
      {items.map((item) => {
        const content = (
          <>
            <div className="name" title={item.label}>
              {item.displayLabel ?? item.label}
            </div>
            <div className="bar-track">
              <div
                className="bar-fill"
                style={{ width: `${max ? (item.value / max) * 100 : 0}%`, background: item.color }}
              />
            </div>
            <div className="num">{item.displayValue ?? item.value}</div>
          </>
        );
        if (!onItemClick) {
          return (
            <div className="bar-row" key={item.label}>
              {content}
            </div>
          );
        }
        return (
          <button
            type="button"
            key={item.label}
            className={`bar-row bar-row-clickable${activeLabel === item.label ? " active" : ""}`}
            onClick={() => onItemClick(item.label)}
          >
            {content}
          </button>
        );
      })}
    </div>
  );
}
