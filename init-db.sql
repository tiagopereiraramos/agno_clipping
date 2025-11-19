-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Create schemas
CREATE SCHEMA IF NOT EXISTS clippings_app;

-- Create tables
CREATE TABLE clippings_app.clipping_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_id VARCHAR(255) UNIQUE NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    instruction TEXT NOT NULL,
    parameters JSONB,
    result_metadata JSONB,
    total_tokens INTEGER,
    total_cost_usd DECIMAL(10, 4),
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    started_at TIMESTAMP,
    completed_at TIMESTAMP
);

CREATE INDEX idx_job_id ON clippings_app.clipping_jobs(job_id);
CREATE INDEX idx_status ON clippings_app.clipping_jobs(status);
CREATE INDEX idx_created_at ON clippings_app.clipping_jobs(created_at);
CREATE INDEX idx_clipping_jobs_status_created ON clippings_app.clipping_jobs(status, created_at DESC);

CREATE TABLE clippings_app.clipping_results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_id VARCHAR(255) NOT NULL REFERENCES clippings_app.clipping_jobs(job_id),
    source_name VARCHAR(255),
    title TEXT NOT NULL,
    author VARCHAR(255),
    date_published TIMESTAMP,
    url TEXT NOT NULL,
    content TEXT,
    s3_uri_json TEXT,
    s3_uri_markdown TEXT,
    s3_uri_pdf TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_results_job_id ON clippings_app.clipping_results(job_id);
CREATE INDEX idx_results_created_at ON clippings_app.clipping_results(created_at);

CREATE TABLE clippings_app.agent_execution_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_id VARCHAR(255) NOT NULL,
    agent_name VARCHAR(100) NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    message TEXT,
    input_tokens INTEGER,
    output_tokens INTEGER,
    cost_usd DECIMAL(10, 4),
    metadata JSONB,
    timestamp TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_execution_job_id ON clippings_app.agent_execution_logs(job_id);
CREATE INDEX idx_execution_agent_name ON clippings_app.agent_execution_logs(agent_name);
CREATE INDEX idx_execution_timestamp ON clippings_app.agent_execution_logs(timestamp);
CREATE INDEX idx_execution_logs_job_agent ON clippings_app.agent_execution_logs(job_id, agent_name);

CREATE TABLE clippings_app.notification_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_id VARCHAR(255) NOT NULL,
    channel VARCHAR(50) NOT NULL,
    recipient VARCHAR(255),
    subject VARCHAR(255),
    status VARCHAR(50) NOT NULL,
    error_message TEXT,
    timestamp TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_notification_job_id ON clippings_app.notification_logs(job_id);
CREATE INDEX idx_notification_channel ON clippings_app.notification_logs(channel);
CREATE INDEX idx_notification_timestamp ON clippings_app.notification_logs(timestamp);

-- Grants
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA clippings_app TO clippings_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA clippings_app TO clippings_user;

