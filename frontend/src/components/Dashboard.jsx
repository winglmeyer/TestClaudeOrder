import { useEffect, useState } from "react";
import { getSalesByDay, getSalesSummary, getTopProducts } from "../api";

const SERIES_COLOR = "#2a78d6";

function formatCurrency(value) {
  return `$${Number(value).toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

function StatTile({ label, value }) {
  return (
    <div className="stat-tile">
      <div className="stat-label">{label}</div>
      <div className="stat-value">{value}</div>
    </div>
  );
}

function BarChart({ data, xKey, yKey, xLabel, formatValue = (v) => v }) {
  const [hoverIndex, setHoverIndex] = useState(null);

  if (data.length === 0) {
    return <p className="empty-state">No data for this range.</p>;
  }

  const width = 640;
  const height = 240;
  const paddingLeft = 8;
  const paddingBottom = 34;
  const chartHeight = height - paddingBottom;
  const maxValue = Math.max(...data.map((d) => d[yKey]), 1);
  const slot = (width - paddingLeft) / data.length;
  const barWidth = Math.min(24, slot * 0.6);
  const maxLabelChars = Math.max(3, Math.floor(slot / 6));

  return (
    <div className="bar-chart-wrap">
      <svg
        viewBox={`0 0 ${width} ${height}`}
        className="bar-chart"
        role="img"
        aria-label={xLabel}
      >
        <line
          x1={paddingLeft}
          y1={chartHeight}
          x2={width}
          y2={chartHeight}
          stroke="#c3c2b7"
          strokeWidth="1"
        />
        {data.map((d, i) => {
          const barHeight = (d[yKey] / maxValue) * (chartHeight - 12);
          const x = paddingLeft + i * slot + (slot - barWidth) / 2;
          const y = chartHeight - barHeight;
          const isHovered = hoverIndex === i;
          return (
            <g key={d[xKey]}>
              <rect
                x={x}
                y={y}
                width={barWidth}
                height={Math.max(barHeight, 1)}
                rx="4"
                fill={SERIES_COLOR}
                opacity={isHovered ? 1 : 0.85}
                onPointerEnter={() => setHoverIndex(i)}
                onPointerLeave={() => setHoverIndex(null)}
                onFocus={() => setHoverIndex(i)}
                onBlur={() => setHoverIndex(null)}
                tabIndex={0}
              >
                <title>{`${d[xKey]}: ${formatValue(d[yKey])}`}</title>
              </rect>
              <text
                x={x + barWidth / 2}
                y={chartHeight + 16}
                textAnchor="middle"
                fontSize="10"
                fill="#898781"
              >
                {String(d[xKey]).length > maxLabelChars
                  ? `${String(d[xKey]).slice(0, maxLabelChars - 1)}…`
                  : d[xKey]}
              </text>
            </g>
          );
        })}
      </svg>
      <div className="bar-chart-tooltip">
        {hoverIndex !== null
          ? `${data[hoverIndex][xKey]} — ${formatValue(data[hoverIndex][yKey])}`
          : " "}
      </div>
    </div>
  );
}

export default function Dashboard() {
  const [range, setRange] = useState({ date_from: "", date_to: "" });
  const [summary, setSummary] = useState(null);
  const [byDay, setByDay] = useState([]);
  const [topProducts, setTopProducts] = useState([]);
  const [error, setError] = useState(null);

  async function refresh(filters) {
    const params = {};
    if (filters.date_from) params.date_from = filters.date_from;
    if (filters.date_to) params.date_to = filters.date_to;
    try {
      setError(null);
      const [summaryData, byDayData, topProductsData] = await Promise.all([
        getSalesSummary(params),
        getSalesByDay(params),
        getTopProducts(params),
      ]);
      setSummary(summaryData);
      setByDay(byDayData);
      setTopProducts(topProductsData);
    } catch (err) {
      setError(err.message);
    }
  }

  useEffect(() => {
    refresh(range);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function handleRangeChange(e) {
    const next = { ...range, [e.target.name]: e.target.value };
    setRange(next);
    refresh(next);
  }

  return (
    <div className="dashboard">
      {error && <p className="form-error">{error}</p>}

      <div className="search-bar">
        <label>
          From
          <input type="date" name="date_from" value={range.date_from} onChange={handleRangeChange} />
        </label>
        <label>
          To
          <input type="date" name="date_to" value={range.date_to} onChange={handleRangeChange} />
        </label>
      </div>

      {summary && (
        <div className="stat-tiles">
          <StatTile label="Total orders" value={summary.total_orders.toLocaleString()} />
          <StatTile label="Total revenue" value={formatCurrency(summary.total_revenue)} />
          <StatTile label="Avg order value" value={formatCurrency(summary.avg_order_value)} />
        </div>
      )}

      <section className="panel">
        <h3>Revenue by day</h3>
        <BarChart
          data={byDay}
          xKey="order_date"
          yKey="revenue"
          xLabel="Revenue by day"
          formatValue={formatCurrency}
        />
      </section>

      <section className="panel">
        <h3>Top products by revenue</h3>
        <BarChart
          data={topProducts}
          xKey="product_id"
          yKey="revenue"
          xLabel="Top products by revenue"
          formatValue={formatCurrency}
        />
      </section>
    </div>
  );
}
