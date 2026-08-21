import {
  BarChart,
  Bar,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  AreaChart,
  Area,
} from 'recharts';

import type { Chart } from '@/services/api';

const PALETTE = [
  '#2563eb',
  '#0891b2',
  '#059669',
  '#d97706',
  '#dc2626',
  '#7c3aed',
  '#db2777',
  '#0d9488',
  '#ea580c',
  '#4f46e5',
];

function fmt(value: unknown): string {
  if (value === null || value === undefined) {
    return '—';
  }

  if (typeof value === 'number') {
    if (Math.abs(value) >= 1000) {
      return value.toLocaleString(
        undefined,
        {
          maximumFractionDigits: 2,
        }
      );
    }

    return Number(
      value.toFixed(3)
    ).toString();
  }

  return String(value);
}

function NoChart({
  message = 'No suitable visualization available for this analysis.',
}: {
  message?: string;
}) {
  return (
    <div className="h-[280px] flex items-center justify-center text-sm text-slate-400">
      {message}
    </div>
  );
}

export default function ChartRenderer({
  chart,
}: {
  chart: Chart;
}) {
  const data = Array.isArray(chart.data)
    ? chart.data
    : [];

  // ----------------------------------------------------------
  // BAR
  // ----------------------------------------------------------

  if (
    chart.type === 'bar' &&
    data.length
  ) {
    return (
      <ResponsiveContainer
        width="100%"
        height={320}
      >
        <BarChart
          data={data}
          margin={{
            top: 10,
            right: 20,
            left: 10,
            bottom: 45,
          }}
        >
          <CartesianGrid
            strokeDasharray="3 3"
            stroke="#e2e8f0"
          />

          <XAxis
            dataKey="category"
            tick={{
              fontSize: 11,
              fill: '#475569',
            }}
            angle={-20}
            textAnchor="end"
            height={65}
          />

          <YAxis
            tick={{
              fontSize: 11,
              fill: '#475569',
            }}
            tickFormatter={fmt}
          />

          <Tooltip
            formatter={(value) =>
              fmt(value)
            }
          />

          <Bar
            dataKey="value"
            fill="#2563eb"
            radius={[
              4,
              4,
              0,
              0,
            ]}
          />
        </BarChart>
      </ResponsiveContainer>
    );
  }

  // ----------------------------------------------------------
  // LINE / AREA
  // ----------------------------------------------------------

  if (
    (
      chart.type === 'line' ||
      chart.type === 'area'
    ) &&
    data.length
  ) {
    return (
      <ResponsiveContainer
        width="100%"
        height={320}
      >
        {chart.type === 'area' ? (
          <AreaChart
            data={data}
            margin={{
              top: 10,
              right: 20,
              left: 10,
              bottom: 35,
            }}
          >
            <CartesianGrid
              strokeDasharray="3 3"
              stroke="#e2e8f0"
            />

            <XAxis
              dataKey="date"
              tick={{
                fontSize: 10,
                fill: '#475569',
              }}
            />

            <YAxis
              tick={{
                fontSize: 11,
                fill: '#475569',
              }}
              tickFormatter={fmt}
            />

            <Tooltip
              formatter={(value) =>
                fmt(value)
              }
            />

            <Area
              type="monotone"
              dataKey="value"
              stroke="#2563eb"
              fill="#bfdbfe"
              strokeWidth={2}
            />
          </AreaChart>
        ) : (
          <LineChart
            data={data}
            margin={{
              top: 10,
              right: 20,
              left: 10,
              bottom: 35,
            }}
          >
            <CartesianGrid
              strokeDasharray="3 3"
              stroke="#e2e8f0"
            />

            <XAxis
              dataKey="date"
              tick={{
                fontSize: 10,
                fill: '#475569',
              }}
            />

            <YAxis
              tick={{
                fontSize: 11,
                fill: '#475569',
              }}
              tickFormatter={fmt}
            />

            <Tooltip
              formatter={(value) =>
                fmt(value)
              }
            />

            <Line
              type="monotone"
              dataKey="value"
              stroke="#2563eb"
              strokeWidth={2}
              dot={false}
            />
          </LineChart>
        )}
      </ResponsiveContainer>
    );
  }

  // ----------------------------------------------------------
  // PIE
  // ----------------------------------------------------------

  if (
    chart.type === 'pie' &&
    data.length
  ) {
    return (
      <ResponsiveContainer
        width="100%"
        height={320}
      >
        <PieChart>
          <Pie
            data={data}
            dataKey="value"
            nameKey="category"
            cx="50%"
            cy="48%"
            outerRadius={105}
            innerRadius={55}
            paddingAngle={2}
            label={(entry: any) =>
              `${entry.category}: ${fmt(
                entry.value
              )}`
            }
          >
            {data.map(
              (_, index) => (
                <Cell
                  key={index}
                  fill={
                    PALETTE[
                      index %
                        PALETTE.length
                    ]
                  }
                />
              )
            )}
          </Pie>

          <Tooltip
            formatter={(value) =>
              fmt(value)
            }
          />

          <Legend
            wrapperStyle={{
              fontSize: 11,
            }}
          />
        </PieChart>
      </ResponsiveContainer>
    );
  }

  // ----------------------------------------------------------
  // SCATTER
  // ----------------------------------------------------------

  if (
    chart.type === 'scatter' &&
    data.length
  ) {
    return (
      <ResponsiveContainer
        width="100%"
        height={320}
      >
        <ScatterChart
          margin={{
            top: 10,
            right: 20,
            left: 10,
            bottom: 35,
          }}
        >
          <CartesianGrid
            strokeDasharray="3 3"
            stroke="#e2e8f0"
          />

          <XAxis
            type="number"
            dataKey="x"
            name={chart.x_label}
            tick={{
              fontSize: 11,
              fill: '#475569',
            }}
            tickFormatter={fmt}
          />

          <YAxis
            type="number"
            dataKey="y"
            name={chart.y_label}
            tick={{
              fontSize: 11,
              fill: '#475569',
            }}
            tickFormatter={fmt}
          />

          <Tooltip
            cursor={{
              strokeDasharray:
                '3 3',
            }}
            formatter={(value) =>
              fmt(value)
            }
          />

          <Scatter
            name={
              chart.title
            }
            data={data}
            fill="#2563eb"
          />
        </ScatterChart>
      </ResponsiveContainer>
    );
  }

  // ----------------------------------------------------------
  // HISTOGRAM
  // ----------------------------------------------------------

  if (
    chart.type === 'histogram' &&
    data.length
  ) {
    return (
      <ResponsiveContainer
        width="100%"
        height={320}
      >
        <BarChart
          data={data}
          margin={{
            top: 10,
            right: 20,
            left: 10,
            bottom: 55,
          }}
        >
          <CartesianGrid
            strokeDasharray="3 3"
            stroke="#e2e8f0"
          />

          <XAxis
            dataKey="category"
            tick={{
              fontSize: 9,
              fill: '#475569',
            }}
            angle={-45}
            textAnchor="end"
            height={75}
            interval="preserveStartEnd"
          />

          <YAxis
            tick={{
              fontSize: 11,
              fill: '#475569',
            }}
            tickFormatter={fmt}
          />

          <Tooltip
            formatter={(value) =>
              fmt(value)
            }
          />

          <Bar
            dataKey="value"
            fill="#0891b2"
          />
        </BarChart>
      </ResponsiveContainer>
    );
  }

  // ----------------------------------------------------------
  // PROPER BOX PLOT
  // ----------------------------------------------------------

  if (
    chart.type === 'box' &&
    data.length
  ) {
    const rows = data
      .filter(
        (row: any) =>
          row &&
          Number.isFinite(
            Number(row.min)
          ) &&
          Number.isFinite(
            Number(row.q1)
          ) &&
          Number.isFinite(
            Number(row.median)
          ) &&
          Number.isFinite(
            Number(row.q3)
          ) &&
          Number.isFinite(
            Number(row.max)
          )
      )
      .slice(0, 10);

    if (!rows.length) {
      return <NoChart />;
    }

    const allValues = rows.flatMap(
      (row: any) => [
        Number(row.min),
        Number(row.max),
      ]
    );

    const min = Math.min(
      ...allValues
    );

    const max = Math.max(
      ...allValues
    );

    const range =
      max - min || 1;

    const height = 280;
    const top = 20;
    const bottom = 45;
    const plotHeight =
      height -
      top -
      bottom;

    const y = (value: number) =>
      top +
      (
        (max - value) /
        range
      ) *
        plotHeight;

    const width = Math.max(
      520,
      rows.length * 80
    );

    return (
      <div className="overflow-x-auto">
        <svg
          width={width}
          height={height}
          viewBox={`0 0 ${width} ${height}`}
        >
          <line
            x1="50"
            y1={top}
            x2={width - 20}
            y2={top}
            stroke="#e2e8f0"
          />

          <line
            x1="50"
            y1={height - bottom}
            x2={width - 20}
            y2={height - bottom}
            stroke="#e2e8f0"
          />

          {rows.map(
            (
              row: any,
              index: number
            ) => {
              const x =
                80 +
                index * 80;

              const boxTop =
                y(Number(row.q3));

              const boxBottom =
                y(Number(row.q1));

              const medianY =
                y(Number(row.median));

              const minY =
                y(Number(row.min));

              const maxY =
                y(Number(row.max));

              return (
                <g
                  key={
                    row.category
                  }
                >
                  <line
                    x1={x}
                    y1={maxY}
                    x2={x}
                    y2={minY}
                    stroke="#64748b"
                    strokeWidth="2"
                  />

                  <line
                    x1={x - 14}
                    y1={maxY}
                    x2={x + 14}
                    y2={maxY}
                    stroke="#64748b"
                    strokeWidth="2"
                  />

                  <line
                    x1={x - 14}
                    y1={minY}
                    x2={x + 14}
                    y2={minY}
                    stroke="#64748b"
                    strokeWidth="2"
                  />

                  <rect
                    x={x - 22}
                    y={boxTop}
                    width="44"
                    height={Math.max(
                      2,
                      boxBottom -
                        boxTop
                    )}
                    fill="#bfdbfe"
                    stroke="#2563eb"
                    strokeWidth="2"
                    rx="3"
                  />

                  <line
                    x1={x - 22}
                    y1={medianY}
                    x2={x + 22}
                    y2={medianY}
                    stroke="#1e3a8a"
                    strokeWidth="3"
                  />

                  <text
                    x={x}
                    y={height - 18}
                    textAnchor="middle"
                    fontSize="10"
                    fill="#475569"
                  >
                    {String(
                      row.category
                    ).slice(0, 12)}
                  </text>
                </g>
              );
            }
          )}

          <text
            x="15"
            y="16"
            fontSize="10"
            fill="#64748b"
          >
            {fmt(max)}
          </text>

          <text
            x="15"
            y={height - bottom}
            fontSize="10"
            fill="#64748b"
          >
            {fmt(min)}
          </text>
        </svg>
      </div>
    );
  }

  // ----------------------------------------------------------
  // HEATMAP
  // ----------------------------------------------------------

  if (
    chart.type === 'heatmap'
  ) {
    const columns =
      chart.columns || [];

    const matrix =
      chart.matrix || [];

    if (
      columns.length === 0 ||
      matrix.length === 0
    ) {
      return <NoChart />;
    }

    const cell = 58;

    const colorFor =
      (value: number | null) => {
        if (
          value === null ||
          value === undefined
        ) {
          return '#f1f5f9';
        }

        const intensity =
          Math.min(
            1,
            Math.abs(value)
          );

        if (value >= 0) {
          return `rgba(37, 99, 235, ${Math.max(
            0.08,
            intensity
          )})`;
        }

        return `rgba(220, 38, 38, ${Math.max(
          0.08,
          intensity
        )})`;
      };

    return (
      <div className="overflow-x-auto">
        <div
          className="grid"
          style={{
            minWidth:
              columns.length *
                cell +
              100,
            gridTemplateColumns:
              `100px repeat(${columns.length}, ${cell}px)`,
          }}
        >
          <div />

          {columns.map(
            (column) => (
              <div
                key={column}
                className="text-[10px] text-slate-500 text-center font-medium px-1 py-1 truncate"
                title={column}
              >
                {column}
              </div>
            )
          )}

          {matrix.map(
            (
              row,
              rowIndex
            ) => (
              <>
                <div
                  key={`label-${rowIndex}`}
                  className="text-[10px] text-slate-600 text-right pr-2 py-1 truncate font-medium"
                  title={
                    columns[rowIndex]
                  }
                >
                  {columns[rowIndex]}
                </div>

                {row.map(
                  (
                    value,
                    columnIndex
                  ) => (
                    <div
                      key={`cell-${rowIndex}-${columnIndex}`}
                      className="flex items-center justify-center text-[10px] font-medium text-slate-700 border border-white"
                      style={{
                        background:
                          colorFor(
                            value
                          ),
                        height:
                          cell - 4,
                        margin: 2,
                        borderRadius: 4,
                      }}
                      title={`${columns[rowIndex]} vs ${columns[columnIndex]}: ${value ?? '—'}`}
                    >
                      {value !== null &&
                      value !== undefined
                        ? value.toFixed(
                            2
                          )
                        : '—'}
                    </div>
                  )
                )}
              </>
            )
          )}
        </div>
      </div>
    );
  }

  return <NoChart />;
}
