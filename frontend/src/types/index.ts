export interface User {
  id: number;
  email: string;
  is_active: boolean;
  is_superuser: boolean;
  created_at: string;
}

export interface Ticket {
  id: number;
  title: string;
  description: string;
  status: 'open' | 'in_progress' | 'resolved' | 'closed';
  user_id: number;
  created_at: string;
  updated_at: string;
}

export interface Message {
  id: number;
  ticket_id: number;
  content: string;
  sender_type: 'user' | 'agent' | 'human_agent';
  created_at: string;
}

export interface AgentRun {
  id: number;
  ticket_id: number;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'needs_escalation';
  result?: string;
  error?: string;
  created_at: string;
  completed_at?: string;
}
