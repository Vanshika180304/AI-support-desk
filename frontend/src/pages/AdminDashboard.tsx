import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../services/api';
import type { Ticket } from '../types';
import { Card } from '../components/common/Card';
import { Button } from '../components/common/Button';
import { Search, Server, Users, Settings } from 'lucide-react';
import '../pages/Dashboard.css'; // Reusing dashboard styles

export const AdminDashboard: React.FC = () => {
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    const fetchAllTickets = async () => {
      try {
        const response = await api.get('/tickets/all'); // Assuming there's an admin endpoint for all tickets
        setTickets(response.data);
      } catch (error) {
        console.error('Failed to fetch all tickets:', error);
      } finally {
        setIsLoading(false);
      }
    };
    fetchAllTickets();
  }, []);

  const handleLogout = () => {
    localStorage.removeItem('token');
    navigate('/login');
  };

  return (
    <div className="dashboard-layout">
      {/* Sidebar Placeholder */}
      <aside className="sidebar">
        <div className="sidebar-header">
          <h2>Admin Control</h2>
        </div>
        <nav className="sidebar-nav">
          <a href="#" className="nav-item active">
            <Server size={18} />
            All Tickets
          </a>
          <a href="#" className="nav-item">
            <Users size={18} />
            Users
          </a>
          <a href="#" className="nav-item">
            <Settings size={18} />
            Knowledge Base
          </a>
        </nav>
        <div className="sidebar-footer">
          <Button variant="ghost" fullWidth onClick={handleLogout}>Logout</Button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="dashboard-main">
        <header className="dashboard-header">
          <div className="header-search">
            <Search size={18} className="search-icon" />
            <input type="text" placeholder="Search across all tickets..." className="search-input" />
          </div>
        </header>

        <div className="dashboard-content animate-fade-in">
          <div className="content-header">
            <h2>Queue Management</h2>
            <p className="text-secondary mt-2">Monitor all incoming user tickets and agent responses.</p>
          </div>

          {isLoading ? (
            <div className="loading-state">Loading all tickets...</div>
          ) : tickets.length === 0 ? (
            <Card className="empty-state">
              <Server size={48} className="empty-icon" />
              <h3>Queue is empty</h3>
              <p>No active tickets in the system.</p>
            </Card>
          ) : (
            <div className="tickets-grid">
              {tickets.map((ticket) => (
                <Card 
                  key={ticket.id} 
                  hoverable 
                  className="ticket-card animate-slide-up"
                  onClick={() => navigate(`/tickets/${ticket.id}`)}
                >
                  <div className="ticket-card-header">
                    <h4>{ticket.title}</h4>
                    <span className={`status-badge status-${ticket.status}`}>
                      {ticket.status.replace('_', ' ')}
                    </span>
                  </div>
                  <p className="ticket-description">
                    {ticket.description.length > 100 
                      ? `${ticket.description.substring(0, 100)}...` 
                      : ticket.description}
                  </p>
                  <div className="ticket-card-footer">
                    <span className="text-xs text-tertiary">User ID: {ticket.user_id}</span>
                    <span className="ticket-date">
                      {new Date(ticket.created_at).toLocaleDateString()}
                    </span>
                  </div>
                </Card>
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  );
};
