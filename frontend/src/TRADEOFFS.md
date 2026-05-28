# Tradeoffs: What I Didn't Build

1. **Authentication / Authorization (JWT/OAuth):**
   * *Why:* I prioritized the core data modeling and parsing engines. In a production environment, both the API and the React frontend would be secured behind token-based authentication with strict Role-Based Access Control (RBAC) to ensure only authorized analysts can approve records.
2. **Asynchronous Task Queues (Celery/Redis):**
   * *Why:* The current API processes file uploads synchronously. For a 4-day prototype and small files, this is fine. For a production app ingesting 5GB SAP dumps, this would block the main thread and timeout. I traded scalability for speed of delivery here. Production would require passing the file to an S3 bucket and triggering a background Celery worker to parse it.
3. **Complex Frontend State Management (Redux/Zustand):**
   * *Why:* The React dashboard uses simple local state (`useState`). Because there is no prop-drilling or complex cross-component data sharing needed for a single dashboard view, adding Redux would be severe over-engineering.