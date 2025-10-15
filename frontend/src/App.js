import { useState, useEffect, useRef } from "react";
import "@/App.css";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import axios from "axios";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Play, Pause, RotateCcw } from "lucide-react";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const TrafficLight = ({ color, isActive, direction }) => {
  return (
    <div className="traffic-light-container" data-testid={`traffic-light-${direction}`}>
      <div className="traffic-light">
        <div className={`light red ${color === 'red' && isActive ? 'active' : ''}`} data-testid={`light-red-${direction}`}></div>
        <div className={`light yellow ${color === 'yellow' && isActive ? 'active' : ''}`} data-testid={`light-yellow-${direction}`}></div>
        <div className={`light green ${color === 'green' && isActive ? 'active' : ''}`} data-testid={`light-green-${direction}`}></div>
      </div>
    </div>
  );
};

const TrafficDashboard = () => {
  const [showSplash, setShowSplash] = useState(true);
  const [trafficData, setTrafficData] = useState({
    north: { vehicles: 0, signal: 'red' },
    south: { vehicles: 0, signal: 'red' },
    east: { vehicles: 0, signal: 'red' },
    west: { vehicles: 0, signal: 'red' }
  });
  const [currentGreen, setCurrentGreen] = useState('north');
  const [isPaused, setIsPaused] = useState(false);
  const [isManual, setIsManual] = useState(false);
  const [insights, setInsights] = useState([]);
  const [cycleCount, setCycleCount] = useState(0);
  const [latestInsight, setLatestInsight] = useState(null);
  const intervalRef = useRef(null);

  useEffect(() => {
    const timer = setTimeout(() => {
      setShowSplash(false);
    }, 3000);
    return () => clearTimeout(timer);
  }, []);

  const fetchTrafficData = async () => {
    try {
      const response = await axios.get(`${API}/traffic/current`);
      const data = response.data;
      setTrafficData({
        north: data.north,
        south: data.south,
        east: data.east,
        west: data.west
      });
      setCurrentGreen(data.current_green);
      setIsPaused(data.is_paused);
      setIsManual(data.is_manual);
      setCycleCount(data.cycle_count);
    } catch (e) {
      console.error('Error fetching traffic data:', e);
    }
  };

  const fetchInsights = async () => {
    try {
      const response = await axios.get(`${API}/traffic/insights`);
      setInsights(response.data.insights);
      if (response.data.insights.length > 0) {
        setLatestInsight(response.data.insights[0]);
      }
    } catch (e) {
      console.error('Error fetching insights:', e);
    }
  };

  const updateTraffic = async () => {
    try {
      const response = await axios.post(`${API}/traffic/update`);
      if (response.data.traffic_data) {
        setTrafficData(response.data.traffic_data);
        setCurrentGreen(response.data.current_green);
        if (response.data.insight) {
          setLatestInsight(response.data.insight);
        }
        await fetchInsights();
      }
    } catch (e) {
      console.error('Error updating traffic:', e);
    }
  };

  useEffect(() => {
    fetchTrafficData();
    fetchInsights();
    
    // Start simulation with first update after 2 seconds
    const initialTimer = setTimeout(() => {
      updateTraffic();
    }, 2000);
    
    // Set up recurring interval
    const interval = setInterval(() => {
      updateTraffic();
    }, 5000);
    
    intervalRef.current = interval;
    
    return () => {
      clearTimeout(initialTimer);
      clearInterval(interval);
    };
  }, []);

  const togglePause = async () => {
    try {
      if (isPaused) {
        await axios.post(`${API}/traffic/resume`);
        setIsPaused(false);
      } else {
        await axios.post(`${API}/traffic/pause`);
        setIsPaused(true);
      }
    } catch (e) {
      console.error('Error toggling pause:', e);
    }
  };

  const toggleManualMode = async (checked) => {
    try {
      if (checked) {
        setIsManual(true);
      } else {
        await axios.post(`${API}/traffic/auto`);
        setIsManual(false);
      }
    } catch (e) {
      console.error('Error toggling manual mode:', e);
    }
  };

  const setManualSignal = async (direction) => {
    if (!isManual) return;
    try {
      const response = await axios.post(`${API}/traffic/manual`, { direction });
      setTrafficData(response.data.traffic_data);
      setCurrentGreen(direction);
    } catch (e) {
      console.error('Error setting manual signal:', e);
    }
  };

  const resetSimulation = async () => {
    try {
      await axios.post(`${API}/traffic/reset`);
      await fetchTrafficData();
      await fetchInsights();
      setLatestInsight(null);
    } catch (e) {
      console.error('Error resetting simulation:', e);
    }
  };

  if (showSplash) {
    return (
      <div className="splash-screen" data-testid="splash-screen">
        <div className="splash-content">
          <div className="splash-icon">🚦</div>
          <h1 className="splash-title">AI Traffic Signal Controller</h1>
          <p className="splash-subtitle">Smart City Simulation</p>
          <div className="splash-loader"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="dashboard" data-testid="traffic-dashboard">
      <header className="dashboard-header">
        <h1 className="header-title" data-testid="header-title">AI Traffic Signal Controller</h1>
        <div className="header-stats">
          <div className="stat" data-testid="cycle-count">
            <span className="stat-label">Cycles</span>
            <span className="stat-value">{cycleCount}</span>
          </div>
        </div>
      </header>

      <div className="main-content">
        <div className="intersection-section">
          <div className="intersection-container">
            {/* North */}
            <div className="road-side north" data-testid="road-north">
              <TrafficLight color={trafficData.north.signal} isActive={true} direction="north" />
              <div className="vehicle-count" data-testid="vehicle-count-north">
                <span className="count-label">North</span>
                <span className="count-value">{trafficData.north.vehicles} vehicles</span>
              </div>
              {isManual && (
                <Button 
                  size="sm" 
                  onClick={() => setManualSignal('north')}
                  className="manual-btn"
                  data-testid="manual-btn-north"
                >
                  Set Green
                </Button>
              )}
            </div>

            {/* Center intersection */}
            <div className="intersection-center">
              <div className="road horizontal"></div>
              <div className="road vertical"></div>
              <div className="center-dot"></div>
            </div>

            {/* South */}
            <div className="road-side south" data-testid="road-south">
              <TrafficLight color={trafficData.south.signal} isActive={true} direction="south" />
              <div className="vehicle-count" data-testid="vehicle-count-south">
                <span className="count-label">South</span>
                <span className="count-value">{trafficData.south.vehicles} vehicles</span>
              </div>
              {isManual && (
                <Button 
                  size="sm" 
                  onClick={() => setManualSignal('south')}
                  className="manual-btn"
                  data-testid="manual-btn-south"
                >
                  Set Green
                </Button>
              )}
            </div>

            {/* East */}
            <div className="road-side east" data-testid="road-east">
              <TrafficLight color={trafficData.east.signal} isActive={true} direction="east" />
              <div className="vehicle-count" data-testid="vehicle-count-east">
                <span className="count-label">East</span>
                <span className="count-value">{trafficData.east.vehicles} vehicles</span>
              </div>
              {isManual && (
                <Button 
                  size="sm" 
                  onClick={() => setManualSignal('east')}
                  className="manual-btn"
                  data-testid="manual-btn-east"
                >
                  Set Green
                </Button>
              )}
            </div>

            {/* West */}
            <div className="road-side west" data-testid="road-west">
              <TrafficLight color={trafficData.west.signal} isActive={true} direction="west" />
              <div className="vehicle-count" data-testid="vehicle-count-west">
                <span className="count-label">West</span>
                <span className="count-value">{trafficData.west.vehicles} vehicles</span>
              </div>
              {isManual && (
                <Button 
                  size="sm" 
                  onClick={() => setManualSignal('west')}
                  className="manual-btn"
                  data-testid="manual-btn-west"
                >
                  Set Green
                </Button>
              )}
            </div>
          </div>
        </div>

        <div className="control-panel">
          <div className="panel-card">
            <h2 className="panel-title">Control Panel</h2>
            <div className="controls">
              <div className="control-item">
                <Button 
                  onClick={togglePause} 
                  className="control-btn"
                  data-testid="pause-resume-btn"
                >
                  {isPaused ? <Play className="icon" /> : <Pause className="icon" />}
                  {isPaused ? 'Resume' : 'Pause'}
                </Button>
              </div>
              <div className="control-item">
                <Button 
                  onClick={resetSimulation} 
                  variant="outline" 
                  className="control-btn"
                  data-testid="reset-btn"
                >
                  <RotateCcw className="icon" />
                  Reset
                </Button>
              </div>
              <div className="control-item manual-toggle" data-testid="manual-mode-toggle">
                <label htmlFor="manual-mode">Manual Mode</label>
                <Switch 
                  id="manual-mode"
                  checked={isManual} 
                  onCheckedChange={toggleManualMode}
                />
              </div>
            </div>
          </div>

          <div className="panel-card status-card">
            <h2 className="panel-title">Current Status</h2>
            <div className="status-content">
              <div className="status-item" data-testid="current-green-signal">
                <span className="status-label">Active Signal:</span>
                <span className="status-value green">{currentGreen.toUpperCase()}</span>
              </div>
              {latestInsight && (
                <div className="ai-explanation" data-testid="ai-explanation">
                  <span className="explanation-label">AI Decision:</span>
                  <p className="explanation-text">{latestInsight.explanation}</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      <div className="insights-section">
        <h2 className="insights-title">AI Insights History</h2>
        <div className="insights-table" data-testid="insights-table">
          {insights.length === 0 ? (
            <div className="no-insights">No insights yet. Start the simulation to see AI decisions.</div>
          ) : (
            <div className="table-container">
              {insights.map((insight, index) => (
                <div key={index} className="insight-row" data-testid={`insight-row-${index}`}>
                  <div className="insight-time">
                    {new Date(insight.timestamp).toLocaleTimeString()}
                  </div>
                  <div className="insight-decision">{insight.decision}</div>
                  <div className="insight-explanation">{insight.explanation}</div>
                  <div className="insight-counts">
                    N:{insight.vehicle_counts.north} S:{insight.vehicle_counts.south} E:{insight.vehicle_counts.east} W:{insight.vehicle_counts.west}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<TrafficDashboard />} />
        </Routes>
      </BrowserRouter>
    </div>
  );
}

export default App;