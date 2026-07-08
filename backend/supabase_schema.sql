-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Create Enums
CREATE TYPE user_role AS ENUM ('admin', 'agent', 'customer');
CREATE TYPE ticket_status AS ENUM ('open', 'routed', 'answered', 'escalated', 'closed');
CREATE TYPE ticket_category AS ENUM ('billing', 'technical', 'general', 'unclassified');
CREATE TYPE message_sender AS ENUM ('user', 'agent', 'human');

-- Create users table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    role user_role NOT NULL DEFAULT 'customer',
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    CONSTRAINT uq_users_email UNIQUE (email)
);
CREATE UNIQUE INDEX ix_users_email ON users (email);

-- Create tickets table
CREATE TABLE tickets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    subject VARCHAR(500) NOT NULL,
    body TEXT NOT NULL,
    status ticket_status NOT NULL DEFAULT 'open',
    category ticket_category NOT NULL DEFAULT 'unclassified',
    confidence_score FLOAT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);
CREATE INDEX ix_tickets_user_id ON tickets (user_id);
CREATE INDEX ix_tickets_status ON tickets (status);
CREATE INDEX ix_tickets_category ON tickets (category);

-- Create messages table
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticket_id UUID NOT NULL REFERENCES tickets(id) ON DELETE CASCADE,
    sender message_sender NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);
CREATE INDEX ix_messages_ticket_id ON messages (ticket_id);

-- Create kb_documents table
CREATE TABLE kb_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(500) NOT NULL,
    source_url VARCHAR(1000),
    content TEXT NOT NULL,
    category VARCHAR(50) NOT NULL,
    embedding vector(1536),
    chunk_index INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);
CREATE INDEX ix_kb_documents_category ON kb_documents (category);

-- Create agent_runs table
CREATE TABLE agent_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticket_id UUID NOT NULL REFERENCES tickets(id) ON DELETE CASCADE,
    agent_name VARCHAR(100) NOT NULL,
    input TEXT,
    output TEXT,
    confidence FLOAT,
    tool_calls JSON,
    latency_ms INTEGER,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);
CREATE INDEX ix_agent_runs_ticket_id ON agent_runs (ticket_id);

-- Create Alembic version table to mark this migration as completed
CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL,
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);
INSERT INTO alembic_version (version_num) VALUES ('0001');
