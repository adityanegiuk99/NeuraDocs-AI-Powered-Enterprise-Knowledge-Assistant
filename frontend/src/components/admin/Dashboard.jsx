import { useState, useEffect } from 'react';
import { admin, documents as docsApi } from '../../services/api';
import {
  BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, PieChart, Pie, Cell
} from 'recharts';
import {
  Activity, Users, FileText, MessageSquare, Clock, TrendingUp,
  Shield, Upload, Trash2, Search, AlertCircle, CheckCircle
} from 'lucide-react';

const COLORS = ['#6366f1', '#8b5cf6', '#a78bfa', '#c4b5fd', '#e0e7ff'];

export default function Dashboard() {
  const [tab, setTab] = useState('overview');
  const [analytics, setAnalytics] = useState(null);
  const [health, setHealth] = useState(null);
  const [users, setUsers] = useState([]);
  const [docs, setDocs] = useState([]);
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [a, h, u, d, l] = await Promise.all([
        admin.queryAnalytics().catch(() => null),
        admin.health().catch(() => null),
        admin.listUsers().catch(() => []),
        docsApi.list().catch(() => []),
        admin.queryLogs({ limit: 20 }).catch(() => []),
      ]);
      setAnalytics(a);
      setHealth(h);
      setUsers(u);
      setDocs(d);
      setLogs(l);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteDoc = async (id) => {
    if (!confirm('Delete this document and all its vectors?')) return;
    try {
      await docsApi.delete(id);
      setDocs(docs.filter(d => d.id !== id));
    } catch (err) {
      alert(err.message);
    }
  };

  const handleRoleChange = async (userId, newRole) => {
    try {
      await admin.updateUser(userId, { role: newRole });
      setUsers(users.map(u => u.id === userId ? { ...u, role: newRole } : u));
    } catch (err) {
      alert(err.message);
    }
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    try {
      const doc = await docsApi.upload(file);
      setDocs([doc, ...docs]);
    } catch (err) {
      alert(err.message);
    }
    e.target.value = '';
  };

  if (loading) {
    return <div className="admin-loading"><div className="spinner" /><p>Loading dashboard...</p></div>;
  }

  const tabs = [
    { id: 'overview', label: 'Overview', icon: Activity },
    { id: 'documents', label: 'Documents', icon: FileText },
    { id: 'users', label: 'Users', icon: Users },
    { id: 'logs', label: 'Query Logs', icon: Search },
    { id: 'health', label: 'System Health', icon: Shield },
  ];

  return (
    <div className="admin-dashboard">
      <div className="admin-header">
        <h1>Admin Dashboard</h1>
        <button className="btn btn-sm" onClick={loadData}>Refresh</button>
      </div>

      <div className="admin-tabs">
        {tabs.map(t => (
          <button
            key={t.id}
            className={`tab ${tab === t.id ? 'active' : ''}`}
            onClick={() => setTab(t.id)}
          >
            <t.icon size={16} />
            <span>{t.label}</span>
          </button>
        ))}
      </div>

      <div className="admin-content">
        {tab === 'overview' && (
          <div className="overview-grid">
            <div className="kpi-card purple">
              <MessageSquare size={24} />
              <div className="kpi-value">{analytics?.total_queries || 0}</div>
              <div className="kpi-label">Total Queries</div>
            </div>
            <div className="kpi-card blue">
              <Clock size={24} />
              <div className="kpi-value">{Math.round(analytics?.avg_latency_ms || 0)}ms</div>
              <div className="kpi-label">Avg Latency</div>
            </div>
            <div className="kpi-card green">
              <TrendingUp size={24} />
              <div className="kpi-value">{Math.round((analytics?.success_rate || 0) * 100)}%</div>
              <div className="kpi-label">Success Rate</div>
            </div>
            <div className="kpi-card orange">
              <FileText size={24} />
              <div className="kpi-value">{docs.length}</div>
              <div className="kpi-label">Documents</div>
            </div>
            <div className="kpi-card pink">
              <Users size={24} />
              <div className="kpi-value">{users.length}</div>
              <div className="kpi-label">Users</div>
            </div>
            <div className="kpi-card teal">
              <Activity size={24} />
              <div className="kpi-value">{analytics?.queries_today || 0}</div>
              <div className="kpi-label">Today's Queries</div>
            </div>

            {/* Charts */}
            <div className="chart-card wide">
              <h3>Query Volume</h3>
              <ResponsiveContainer width="100%" height={250}>
                <BarChart data={[
                  { name: 'Today', queries: analytics?.queries_today || 0 },
                  { name: 'This Week', queries: analytics?.queries_this_week || 0 },
                  { name: 'Total', queries: analytics?.total_queries || 0 },
                ]}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#2a2a3e" />
                  <XAxis dataKey="name" stroke="#888" />
                  <YAxis stroke="#888" />
                  <Tooltip contentStyle={{ background: '#1e1e2e', border: '1px solid #333', borderRadius: '8px' }} />
                  <Bar dataKey="queries" fill="#6366f1" radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>

            <div className="chart-card">
              <h3>Documents by Status</h3>
              <ResponsiveContainer width="100%" height={250}>
                <PieChart>
                  <Pie
                    data={[
                      { name: 'Ready', value: docs.filter(d => d.status === 'ready').length || 1 },
                      { name: 'Processing', value: docs.filter(d => d.status === 'processing').length },
                      { name: 'Failed', value: docs.filter(d => d.status === 'failed').length },
                    ].filter(d => d.value > 0)}
                    cx="50%" cy="50%" innerRadius={50} outerRadius={80}
                    paddingAngle={4} dataKey="value"
                  >
                    {COLORS.map((color, i) => <Cell key={i} fill={color} />)}
                  </Pie>
                  <Tooltip contentStyle={{ background: '#1e1e2e', border: '1px solid #333', borderRadius: '8px' }} />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}

        {tab === 'documents' && (
          <div className="section">
            <div className="section-header">
              <h2>Document Management</h2>
              <label className="btn btn-primary upload-btn">
                <Upload size={16} /> Upload Document
                <input type="file" accept=".pdf,.docx,.txt" onChange={handleFileUpload} hidden />
              </label>
            </div>
            <div className="table-wrapper">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Filename</th>
                    <th>Type</th>
                    <th>Department</th>
                    <th>Status</th>
                    <th>Chunks</th>
                    <th>Size</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {docs.map(doc => (
                    <tr key={doc.id}>
                      <td className="filename">{doc.original_filename}</td>
                      <td><span className="badge">{doc.file_type}</span></td>
                      <td>{doc.department || '—'}</td>
                      <td>
                        <span className={`status-badge ${doc.status}`}>
                          {doc.status === 'ready' ? <CheckCircle size={12} /> : <AlertCircle size={12} />}
                          {doc.status}
                        </span>
                      </td>
                      <td>{doc.chunk_count}</td>
                      <td>{(doc.file_size / 1024).toFixed(1)} KB</td>
                      <td>
                        <button className="btn btn-sm btn-danger" onClick={() => handleDeleteDoc(doc.id)}>
                          <Trash2 size={14} />
                        </button>
                      </td>
                    </tr>
                  ))}
                  {docs.length === 0 && (
                    <tr><td colSpan={7} className="empty-text">No documents uploaded yet</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {tab === 'users' && (
          <div className="section">
            <h2>User Management</h2>
            <div className="table-wrapper">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Username</th>
                    <th>Email</th>
                    <th>Role</th>
                    <th>Status</th>
                    <th>Joined</th>
                  </tr>
                </thead>
                <tbody>
                  {users.map(u => (
                    <tr key={u.id}>
                      <td>{u.username}</td>
                      <td>{u.email}</td>
                      <td>
                        <select
                          value={u.role}
                          onChange={(e) => handleRoleChange(u.id, e.target.value)}
                          className="role-select"
                        >
                          <option value="admin">Admin</option>
                          <option value="hr">HR</option>
                          <option value="engineer">Engineer</option>
                        </select>
                      </td>
                      <td>
                        <span className={`status-badge ${u.is_active ? 'ready' : 'failed'}`}>
                          {u.is_active ? 'Active' : 'Inactive'}
                        </span>
                      </td>
                      <td>{new Date(u.created_at).toLocaleDateString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {tab === 'logs' && (
          <div className="section">
            <h2>Query Logs</h2>
            <div className="table-wrapper">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Query</th>
                    <th>Status</th>
                    <th>Latency</th>
                    <th>Confidence</th>
                    <th>Feedback</th>
                    <th>Time</th>
                  </tr>
                </thead>
                <tbody>
                  {logs.map(log => (
                    <tr key={log.id}>
                      <td className="query-text">{log.query_text?.slice(0, 60)}...</td>
                      <td>
                        <span className={`status-badge ${log.status}`}>{log.status}</span>
                      </td>
                      <td>{Math.round(log.total_latency_ms || 0)}ms</td>
                      <td>{log.confidence_score ? `${Math.round(log.confidence_score * 100)}%` : '—'}</td>
                      <td>{log.user_feedback ? `${log.user_feedback}/5 ⭐` : '—'}</td>
                      <td>{new Date(log.created_at).toLocaleString()}</td>
                    </tr>
                  ))}
                  {logs.length === 0 && (
                    <tr><td colSpan={6} className="empty-text">No queries yet</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {tab === 'health' && health && (
          <div className="health-grid">
            <div className={`health-card ${health.status}`}>
              <h3>System Status</h3>
              <div className="health-status">{health.status.toUpperCase()}</div>
              <p>Uptime: {Math.round(health.uptime_seconds / 60)} min</p>
              <p>Version: {health.version}</p>
            </div>
            {Object.entries(health.components).map(([name, status]) => (
              <div key={name} className={`health-card ${status === 'ok' ? 'healthy' : 'degraded'}`}>
                <h4>{name.replace(/_/g, ' ')}</h4>
                <div className="component-status">
                  {status === 'ok' ? <CheckCircle size={20} /> : <AlertCircle size={20} />}
                  <span>{status}</span>
                </div>
              </div>
            ))}
            <div className="health-card healthy">
              <h4>Data</h4>
              <p>{health.total_documents} documents</p>
              <p>{health.total_chunks} chunks indexed</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
