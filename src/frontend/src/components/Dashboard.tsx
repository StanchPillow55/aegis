import { useState, useEffect } from 'react';
import ChartWidget from './ChartWidget';
import { format, parseISO } from 'date-fns';
import { useAIContext } from '../context/AIContext';

export default function Dashboard() {
  const { setPage } = useAIContext();
  const [hrvData, setHrvData] = useState<any[]>([]);
  const [weightData, setWeightData] = useState<any[]>([]);
  const [alerts, setAlerts] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    setPage('Dashboard');
  }, []);

  const fetchData = async () => {
    try {
      // Fetch HRV
      const resHrv = await fetch('/api/metrics?metric_type=hrv');
      if (resHrv.ok) {
        const hrv = await resHrv.json();
        setHrvData(hrv.map((m: any) => ({
          date: format(parseISO(m.timestamp), 'MMM d'),
          value: m.value
        })));
      }

      // Fetch Weight
      const resWeight = await fetch('/api/metrics?metric_type=weight');
      if (resWeight.ok) {
        const weight = await resWeight.json();
        setWeightData(weight.map((m: any) => ({
          date: format(parseISO(m.timestamp), 'MMM d'),
          value: m.value
        })));
      }

      // Fetch Alerts
      const resAlerts = await fetch('/api/alerts');
      if (resAlerts.ok) {
        const fetchedAlerts = await resAlerts.json();
        setAlerts(fetchedAlerts);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    // Refresh every 10 seconds to catch new logs
    const intv = setInterval(fetchData, 10000);
    return () => clearInterval(intv);
  }, []);

  if (isLoading) {
    return <div className="animate-fade-in text-subtle">Loading your data...</div>;
  }

  const hasData = hrvData.length > 0 || weightData.length > 0;

  return (
    <div className="dashboard-grid animate-fade-in">
      {!hasData ? (
        <div className="glass-panel" style={{ padding: '2rem', gridColumn: '1 / -1', textAlign: 'center' }}>
          <h2 className="heading-2" style={{ color: 'var(--text-primary)' }}>No Health Data Found</h2>
          <p className="text-subtle" style={{ fontSize: '1rem', marginBottom: '1.5rem' }}>
            It looks like you haven't synced your Fitbit or logged any manual data yet.
          </p>
          <div style={{ display: 'flex', gap: '1rem', justifyContent: 'center' }}>
            <button className="btn btn-primary" onClick={() => document.querySelector<HTMLButtonElement>('.btn-primary')?.click()}>Add Manual Log</button>
          </div>
        </div>
      ) : (
        <>
          <ChartWidget 
            title="Heart Rate Variability (HRV)" 
            data={hrvData} 
            dataKey="value"
            color="var(--accent-primary)"
            goalValue={60} // Hardcoded for display, could be fetched from /api/goals
            goalLabel="Target HRV"
            goalDirection="increase"
            unit="ms"
          />
          
          <ChartWidget 
            title="Body Weight Trend" 
            data={weightData} 
            dataKey="value"
            color="var(--accent-secondary)"
            goalValue={175}
            goalLabel="Goal Weight"
            goalDirection="decrease"
            unit="lbs"
          />
        </>
      )}
      
      <div className="glass-panel" style={{ padding: '1.5rem', display: 'flex', flexDirection: 'column' }}>
        <h3 className="heading-2" style={{ fontSize: '1.125rem' }}>Active Alerts</h3>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', marginTop: '1rem', flex: 1, overflowY: 'auto' }}>
          {alerts.length === 0 ? (
            <div className="text-subtle" style={{ textAlign: 'center', marginTop: '2rem' }}>No active alerts. You're doing great!</div>
          ) : (
            alerts.map((alert, i) => (
              <div key={i} style={{ 
                padding: '1rem', 
                background: alert.severity === 'critical' ? 'rgba(239, 68, 68, 0.1)' : 'rgba(245, 158, 11, 0.1)', 
                borderLeft: `4px solid ${alert.severity === 'critical' ? 'var(--accent-danger)' : 'var(--accent-warning)'}`, 
                borderRadius: '4px' 
              }}>
                <div style={{ fontWeight: 600, color: alert.severity === 'critical' ? 'var(--accent-danger)' : 'var(--accent-warning)', textTransform: 'capitalize' }}>
                  {alert.metric} - {alert.severity}
                </div>
                <div className="text-subtle" style={{ marginTop: '0.25rem' }}>{alert.message}</div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
