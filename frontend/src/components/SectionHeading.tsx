interface Props {
  title: string;
  color: string;
}

/** Groups the dashboard's 20+ cards into named zones so the page reads as a
 * structured console instead of a flat scroll. The colored dot ties each
 * zone to a consistent identity as you scan down the page. */
export function SectionHeading({ title, color }: Props) {
  return (
    <div className="section-heading">
      <span className="section-dot" style={{ background: color }} />
      <span className="section-title">{title}</span>
      <span className="section-rule" />
    </div>
  );
}
