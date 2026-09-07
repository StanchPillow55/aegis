import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip, ReferenceLine, CartesianGrid } from 'recharts';

interface ChartWidgetProps {
  title: string;
  data: any[];
  dataKey: string;
  color: string;
  goalValue?: number;
  goalLabel?: string;
  goalDirection?: 'increase' | 'decrease';
  unit?: string;
}

export default function ChartWidget({ 
  title, 
  data, 
  dataKey, 
  color, 
  goalValue, 
  goalLabel,
  goalDirection,
  unit = ''
}: ChartWidgetProps) {
  
  // Dynamic gradient ID based on title to ensure unique gradients
  const gradientId = `color-${title.replace(/\\s+/g, '-').toLowerCase()}`;
  
  return (
    <div className="glass-panel" style={{ padding: '1.5rem', height: '350px', display: 'flex', flexDirection: 'column' }}>
      <h3 className="heading-2" style={{ fontSize: '1.125rem' }}>{title}</h3>
      <div style={{ flex: 1, marginTop: '1rem', width: '100%', minHeight: 0 }}>
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
            <defs>
              <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={color} stopOpacity={0.8}/>
                <stop offset="95%" stopColor={color} stopOpacity={0}/>
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
            <XAxis dataKey="date" stroke="var(--text-muted)" fontSize={12} tickLine={false} axisLine={false} />
            <YAxis stroke="var(--text-muted)" fontSize={12} tickLine={false} axisLine={false} />
            <Tooltip 
              contentStyle={{ 
                backgroundColor: 'rgba(15, 17, 26, 0.9)', 
                borderColor: 'var(--border-color)',
                borderRadius: '8px',
                boxShadow: 'var(--shadow-panel)'
              }}
              itemStyle={{ color: 'var(--text-primary)' }}
            />
            {goalValue !== undefined && (
              <ReferenceLine 
                y={goalValue} 
                stroke={goalDirection === 'increase' ? 'var(--accent-success)' : 'var(--accent-primary)'} 
                strokeDasharray="5 5" 
                label={{ position: 'top', value: `${goalLabel} (${goalValue}${unit})`, fill: 'var(--text-secondary)', fontSize: 12 }} 
              />
            )}
            <Area 
              type="monotone" 
              dataKey={dataKey} 
              stroke={color} 
              strokeWidth={3}
              fillOpacity={1} 
              fill={`url(#${gradientId})`} 
              animationDuration={1500}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
