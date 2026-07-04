export interface BarItem {
  label: string;
  value: number;
  color: string;
  displayValue?: string;
}

interface Props {
  items: BarItem[];
  maxValue?: number;
}

export function BarList({ items, maxValue }: Props) {
  const max = maxValue ?? Math.max(...items.map((i) => i.value), 1);
  return (
    <div className="barlist">
      {items.map((item) => (
        <div className="bar-row" key={item.label}>
          <div className="name" title={item.label}>
            {item.label}
          </div>
          <div className="bar-track">
            <div
              className="bar-fill"
              style={{ width: `${max ? (item.value / max) * 100 : 0}%`, background: item.color }}
            />
          </div>
          <div className="num">{item.displayValue ?? item.value}</div>
        </div>
      ))}
    </div>
  );
}
