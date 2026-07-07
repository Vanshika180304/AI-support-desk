import React, { useEffect, useState, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { api } from '../services/api';
import { Ticket, Message } from '../types';
import { Card } from '../components/common/Card';
import { Button } from '../components/common/Button';
import { Input } from '../components/common/Input';
import { Send, ArrowLeft, Bot, User, UserCheck } from 'lucide-react';
import './TicketDetail.css';

export const TicketDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [ticket, setTicket] = useState<Ticket | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [newMessage, setNewMessage] = useState('');
  const [isSending, setIsSending] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const fetchTicketData = async () => {
      try {
        const [ticketRes, messagesRes] = await Promise.all([
          api.get(`/tickets/${id}`),
          api.get(`/tickets/${id}/messages`)
        ]);
        setTicket(ticketRes.data);
        setMessages(messagesRes.data);
      } catch (error) {
        console.error('Failed to fetch ticket data:', error);
      } finally {
        setIsLoading(false);
      }
    };
    if (id) fetchTicketData();
    
    // Auto-refresh messages every 5 seconds if ticket is open
    const interval = setInterval(() => {
      if (id) {
        api.get(`/tickets/${id}/messages`).then(res => {
          // Only update if we have new messages
          if (res.data.length > messages.length) {
            setMessages(res.data);
          }
        });
      }
    }, 5000);
    
    return () => clearInterval(interval);
  }, [id, messages.length]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newMessage.trim() || !id) return;

    setIsSending(true);
    try {
      const response = await api.post(`/tickets/${id}/messages`, {
        content: newMessage
      });
      setMessages([...messages, response.data]);
      setNewMessage('');
    } catch (error) {
      console.error('Failed to send message:', error);
    } finally {
      setIsSending(false);
    }
  };

  if (isLoading) {
    return <div className="loading-state">Loading ticket details...</div>;
  }

  if (!ticket) {
    return <div className="loading-state">Ticket not found</div>;
  }

  return (
    <div className="ticket-detail-layout">
      <header className="detail-header glass">
        <div className="header-left">
          <Button variant="ghost" onClick={() => navigate('/dashboard')} leftIcon={<ArrowLeft size={18} />}>
            Back
          </Button>
          <div className="header-info">
            <h2>{ticket.title}</h2>
            <span className={`status-badge status-${ticket.status}`}>
              {ticket.status.replace('_', ' ')}
            </span>
          </div>
        </div>
      </header>

      <main className="chat-container">
        <div className="messages-area">
          <div className="message-wrapper system-message">
            <div className="message-bubble system">
              <p><strong>Ticket Created:</strong> {ticket.description}</p>
            </div>
          </div>
          
          {messages.map((msg) => (
            <div key={msg.id} className={`message-wrapper ${msg.sender_type === 'user' ? 'sent' : 'received'}`}>
              <div className="message-avatar">
                {msg.sender_type === 'agent' ? <Bot size={20} /> : 
                 msg.sender_type === 'human_agent' ? <UserCheck size={20} /> : <User size={20} />}
              </div>
              <div className={`message-bubble ${msg.sender_type}`}>
                <div className="message-sender">
                  {msg.sender_type === 'agent' ? 'AI Assistant' : 
                   msg.sender_type === 'human_agent' ? 'Support Agent' : 'You'}
                </div>
                <div className="message-content">{msg.content}</div>
                <div className="message-time">
                  {new Date(msg.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </div>
              </div>
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>

        <div className="chat-input-area glass">
          <form onSubmit={handleSendMessage} className="chat-form">
            <Input
              fullWidth
              placeholder="Type your message..."
              value={newMessage}
              onChange={(e) => setNewMessage(e.target.value)}
              disabled={ticket.status === 'closed'}
            />
            <Button 
              type="submit" 
              disabled={!newMessage.trim() || ticket.status === 'closed'} 
              isLoading={isSending}
              className="send-btn"
            >
              <Send size={18} />
            </Button>
          </form>
          {ticket.status === 'closed' && (
            <div className="closed-notice text-center mt-2 text-sm text-[var(--text-tertiary)]">
              This ticket is closed.
            </div>
          )}
        </div>
      </main>
    </div>
  );
};
