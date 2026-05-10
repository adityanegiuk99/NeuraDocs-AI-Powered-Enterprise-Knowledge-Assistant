import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import ProtectedRoute from './components/auth/ProtectedRoute';
import Sidebar from './components/shared/Sidebar';
import LoginForm from './components/auth/LoginForm';
import ChatWindow from './components/chat/ChatWindow';
import Dashboard from './components/admin/Dashboard';

function AppLayout({ children }) {
  return (
    <div className="app-layout">
      <Sidebar />
      <main className="main-content">
        {children}
      </main>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginForm />} />

          <Route path="/chat" element={
            <ProtectedRoute>
              <AppLayout><ChatWindow /></AppLayout>
            </ProtectedRoute>
          } />

          <Route path="/documents" element={
            <ProtectedRoute roles={['admin', 'hr']}>
              <AppLayout><Dashboard /></AppLayout>
            </ProtectedRoute>
          } />

          <Route path="/admin" element={
            <ProtectedRoute roles={['admin']}>
              <AppLayout><Dashboard /></AppLayout>
            </ProtectedRoute>
          } />

          <Route path="*" element={<Navigate to="/chat" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
