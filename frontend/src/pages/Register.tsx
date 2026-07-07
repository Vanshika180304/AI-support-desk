import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../services/api';
import { Button } from '../components/common/Button';
import { Input } from '../components/common/Input';
import { Card } from '../components/common/Card';
import './Login.css'; // Reusing the same CSS for identical layout

export const Register: React.FC = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError('');

    if (password !== confirmPassword) {
      setError('Passwords do not match');
      setIsLoading(false);
      return;
    }

    try {
      // API expects email and password
      await api.post('/auth/signup', { email, password });
      
      // Auto-login after successful registration
      // The backend login endpoint might expect form data or JSON.
      // We will match whatever is in Login.tsx for consistency or simply redirect to login.
      navigate('/login');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Registration failed. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="login-container">
      <div className="login-background-glow" />
      <Card className="login-card glass animate-slide-up">
        <div className="login-header">
          <h1 className="login-title">Support Desk</h1>
          <p className="login-subtitle">Create a new account</p>
        </div>

        <form onSubmit={handleRegister} className="login-form">
          <Input
            label="Email Address"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
            required
          />
          <Input
            label="Password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="••••••••"
            required
            minLength={8}
          />
          <Input
            label="Confirm Password"
            type="password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            placeholder="••••••••"
            required
            minLength={8}
          />
          
          {error && <div className="login-error animate-fade-in">{error}</div>}

          <Button 
            type="submit" 
            fullWidth 
            size="lg" 
            isLoading={isLoading}
            className="login-submit-btn"
          >
            Register
          </Button>
        </form>

        <div className="login-footer">
          <p>Already have an account? <a href="/login">Sign in</a></p>
        </div>
      </Card>
    </div>
  );
};
