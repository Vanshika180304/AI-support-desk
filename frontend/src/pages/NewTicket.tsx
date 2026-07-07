import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../services/api';
import { Card } from '../components/common/Card';
import { Button } from '../components/common/Button';
import { Input } from '../components/common/Input';
import { ArrowLeft } from 'lucide-react';

export const NewTicket: React.FC = () => {
  const navigate = useNavigate();
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim() || !description.trim()) return;

    setIsLoading(true);
    setError('');

    try {
      const response = await api.post('/tickets', {
        title,
        description,
      });
      navigate(`/tickets/${response.data.id}`);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to create ticket.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="dashboard-layout">
      <main className="dashboard-main p-8" style={{ padding: '2rem' }}>
        <div className="max-w-3xl mx-auto w-full" style={{ maxWidth: '800px', margin: '0 auto' }}>
          <Button variant="ghost" onClick={() => navigate('/dashboard')} leftIcon={<ArrowLeft size={18} />} className="mb-6" style={{ marginBottom: '1.5rem' }}>
            Back to Dashboard
          </Button>

          <Card className="animate-slide-up">
            <h2 style={{ fontSize: '1.5rem', marginBottom: '1.5rem' }}>Create New Support Ticket</h2>
            
            <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
              <Input
                label="Ticket Title"
                placeholder="e.g., Cannot access billing dashboard"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                required
              />
              
              <div className="input-wrapper full-width">
                <label className="input-label">Description</label>
                <textarea 
                  className="input-field" 
                  style={{ minHeight: '150px', resize: 'vertical' }}
                  placeholder="Please describe your issue in detail..."
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  required
                />
              </div>

              {error && <div className="login-error animate-fade-in">{error}</div>}

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '1rem', marginTop: '1rem' }}>
                <Button variant="secondary" onClick={() => navigate('/dashboard')} type="button">
                  Cancel
                </Button>
                <Button type="submit" isLoading={isLoading}>
                  Submit Ticket
                </Button>
              </div>
            </form>
          </Card>
        </div>
      </main>
    </div>
  );
};
