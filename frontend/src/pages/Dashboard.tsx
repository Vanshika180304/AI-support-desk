import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../services/api';
import type { Ticket } from '../types';
import { Card } from '../components/common/Card';
import { Button } from '../components/common/Button';
import { Plus, Search, MessageSquare } from 'lucide-react';
import './Dashboard.css';

export const Dashboard: React.FC = () => {
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    const fetchTickets = async () => {
      try {
        const response = await api.get('/tickets');
        setTickets(response.data);
      } catch (error) {
        console.error('Failed to fetch tickets:', error);
      } finally {
        setIsLoading(false);
      }
    };
    fetchTickets();
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
          <h2>Support Desk</h2>
        </div>
        <nav className="sidebar-nav">
          <a href="#" className="nav-item active">
            <MessageSquare size={18} />
            My Tickets
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
            <input type="text" placeholder="Search tickets..." className="search-input" />
          </div>
          <Button leftIcon={<Plus size={18} />} onClick={() => navigate('/tickets/new')}>
            New Ticket
          </Button>
        </header>

        <div className="dashboard-content animate-fade-in">
          <div className="content-header">
            <h2>Your Support Tickets</h2>
          </div>

          {isLoading ? (
            <div className="loading-state">Loading tickets...</div>
          ) : tickets.length === 0 ? (
            <Card className="empty-state">
              <MessageSquare size={48} className="empty-icon" />
              <h3>No tickets yet</h3>
              <p>Create a new ticket to get help from our AI agents.</p>
              <Button leftIcon={<Plus size={18} />} onClick={() => navigate('/tickets/new')} className="mt-4">
                Create Ticket
              </Button>
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
