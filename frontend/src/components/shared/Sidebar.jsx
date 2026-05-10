import { NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import {
  MessageSquare, FileText, LayoutDashboard, LogOut, Shield, Bot
} from 'lucide-react';

export default function Sidebar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <Bot size={28} />
        <span>KnowledgeAI</span>
      </div>

      <nav className="sidebar-nav">
        <NavLink to="/chat" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
          <MessageSquare size={18} />
          <span>Chat</span>
        </NavLink>

        {(user?.role === 'admin' || user?.role === 'hr') && (
          <NavLink to="/documents" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
            <FileText size={18} />
            <span>Documents</span>
          </NavLink>
        )}

        {user?.role === 'admin' && (
          <NavLink to="/admin" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
            <LayoutDashboard size={18} />
            <span>Admin</span>
          </NavLink>
        )}
      </nav>

      <div className="sidebar-footer">
        <div className="user-info">
          <div className="user-avatar">{user?.username?.[0]?.toUpperCase() || '?'}</div>
          <div className="user-details">
            <span className="user-name">{user?.username}</span>
            <span className="user-role">
              <Shield size={12} />
              {user?.role}
            </span>
          </div>
        </div>
        <button className="logout-btn" onClick={handleLogout} title="Logout">
          <LogOut size={18} />
        </button>
      </div>
    </aside>
  );
}
