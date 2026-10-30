import { useState, useEffect } from 'react';
import './PublicPage.css';

const API_URL = 'http://127.0.0.1:8000';
const STORAGE_KEY = 'ekr_public_api_key';

function PublicPage() {
  const [apiKey, setApiKey] = useState(sessionStorage.getItem(STORAGE_KEY) || '');
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [loginLoading, setLoginLoading] = useState(false);
  const [documentsLoading, setDocumentsLoading] = useState(false);
  const [chatLoading, setChatLoading] = useState(false);
  const [documents, setDocuments] = useState([]);
  const [selectedDocument, setSelectedDocument] = useState(null);
  const [pdfUrl, setPdfUrl] = useState('');
  const [pdfLoading, setPdfLoading] = useState(false);
  const [pdfError, setPdfError] = useState('');
  const [question, setQuestion] = useState('');
  const [messages, setMessages] = useState([]);
  const [loginError, setLoginError] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    const savedKey = sessionStorage.getItem(STORAGE_KEY);
    if (savedKey) verifyPublicKey(savedKey);
  }, []);

  useEffect(() => {
    if (!selectedDocument || !apiKey) {
      setPdfUrl('');
      setPdfError('');
      return;
    }

    const filename = getFilename(selectedDocument);

    if (!filename.toLowerCase().endsWith('.pdf')) {
      setPdfUrl('');
      setPdfError('Preview is currently available only for PDF documents.');
      return;
    }

    const controller = new AbortController();
    let objectUrl = '';

    const loadPdf = async () => {
      setPdfLoading(true);
      setPdfError('');
      setPdfUrl('');

      try {
        const response = await fetch(
          `${API_URL}/api/documents/${selectedDocument.document_id}/file`,
          {
            headers: { 'X-API-Key': apiKey },
            signal: controller.signal,
          }
        );

        if (!response.ok) {
          const data = await response.json().catch(() => ({}));
          throw new Error(data.detail || 'Unable to load PDF document.');
        }

        objectUrl = URL.createObjectURL(await response.blob());
        setPdfUrl(objectUrl);
      } catch (err) {
        if (err.name !== 'AbortError') {
          setPdfError(err.message);
        }
      } finally {
        if (!controller.signal.aborted) {
          setPdfLoading(false);
        }
      }
    };

    loadPdf();

    return () => {
      controller.abort();
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [selectedDocument, apiKey]);

  const verifyPublicKey = async (key) => {
    setLoginLoading(true);
    setLoginError('');

    try {
      const response = await fetch(`${API_URL}/api/auth/me`, {
        headers: { 'X-API-Key': key },
      });

      if (!response.ok) {
        throw new Error('Invalid API key. Please try again.');
      }

      const data = await response.json();

      if (data.role !== 'public') {
        throw new Error('Please use a Public API key.');
      }

      sessionStorage.setItem(STORAGE_KEY, key);
      setApiKey(key);
      setIsAuthenticated(true);
      await fetchDocuments(key);
    } catch (err) {
      sessionStorage.removeItem(STORAGE_KEY);
      setIsAuthenticated(false);
      setLoginError(err.message);
    } finally {
      setLoginLoading(false);
    }
  };

  const handleLogin = async (event) => {
    event.preventDefault();

    if (!apiKey.trim()) {
      setLoginError('Please enter your Public API key.');
      return;
    }

    await verifyPublicKey(apiKey.trim());
  };

  const fetchDocuments = async (key = apiKey) => {
    setDocumentsLoading(true);
    setError('');

    try {
      const response = await fetch(`${API_URL}/api/documents`, {
        headers: { 'X-API-Key': key },
      });

      if (!response.ok) {
        throw new Error('Unable to load documents.');
      }

      const data = await response.json();
      const documentList = Array.isArray(data)
        ? data
        : data.documents || [];

      setDocuments(documentList);

      setSelectedDocument((current) => {
        if (!current) return null;

        return documentList.find(
          (doc) => doc.document_id === current.document_id
        ) || null;
      });
    } catch (err) {
      setError(err.message);
    } finally {
      setDocumentsLoading(false);
    }
  };

  const handleAskQuestion = async (event) => {
    event.preventDefault();

    if (!question.trim() || chatLoading) return;

    const userQuestion = question.trim();

    setMessages((previous) => [
      ...previous,
      { type: 'user', content: userQuestion },
    ]);

    setQuestion('');
    setChatLoading(true);
    setError('');

    try {
      const response = await fetch(`${API_URL}/api/ask`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': apiKey,
        },
        body: JSON.stringify({ question: userQuestion }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Unable to get an answer.');
      }

      const data = await response.json();

      setMessages((previous) => [
        ...previous,
        {
          type: 'assistant',
          content: data.answer || 'No answer returned.',
          sources: data.sources || [],
          cacheStatus: data.cache_status || 'N/A',
        },
      ]);
    } catch (err) {
      setMessages((previous) => [
        ...previous,
        {
          type: 'assistant',
          content: `Error: ${err.message}`,
          sources: [],
          cacheStatus: 'N/A',
        },
      ]);
    } finally {
      setChatLoading(false);
    }
  };

  const handleLogout = () => {
    sessionStorage.removeItem(STORAGE_KEY);
    setApiKey('');
    setIsAuthenticated(false);
    setDocuments([]);
    setSelectedDocument(null);
    setPdfUrl('');
    setMessages([]);
    setQuestion('');
    setError('');
    setLoginError('');
  };

  const getFilename = (document) =>
    document?.filename ||
    document?.document ||
    document?.name ||
    'Unknown document';

  const versionCount = documents.reduce((total, doc) => {
    const value = Number(doc.version_count ?? doc.versions_count ?? 1);

    return total + (
      Number.isFinite(value) && value > 0 ? value : 1
    );
  }, 0);

  if (!isAuthenticated) {
    return (
      <div className="public-login-page">
        <div className="public-login-brand">
          <div className="public-logo">EKR</div>
          <span>Enterprise Knowledge Retrieval</span>
        </div>

        <div className="public-login-content">
          <div className="public-login-card">
            <div className="public-login-icon">🔐</div>
            <h1>Public Workspace</h1>

            <p>
              Securely access your enterprise knowledge base
              and interact with the AI assistant.
            </p>

            <form onSubmit={handleLogin}>
              <label htmlFor="public-api-key">Public API Key</label>

              <input
                id="public-api-key"
                type="password"
                value={apiKey}
                onChange={(event) => setApiKey(event.target.value)}
                placeholder="Enter your Public API key"
                autoComplete="off"
              />

              {loginError && (
                <p className="public-login-error">{loginError}</p>
              )}

              <button type="submit" disabled={loginLoading}>
                {loginLoading ? 'Verifying...' : 'Access Workspace'}
              </button>
            </form>

            <div className="public-login-footer">
              Protected Enterprise Knowledge Access
            </div>
          </div>
        </div>
      </div>
    );
  }
    return (
    <div className="public-dashboard">
      <aside className="public-sidebar">
        <div className="public-sidebar-brand">
          <div className="public-logo">EKR</div>
          <div>
            <h2>EKR Workspace</h2>
            <span>Knowledge Retrieval</span>
          </div>
        </div>

        <div className="public-sidebar-section">
          <p className="public-sidebar-heading">WORKSPACE</p>

          <button className="public-nav-item active">
            <span>⌂</span> Home
          </button>

          <button
            className="public-nav-item"
            onClick={() => document.getElementById('your-documents')?.scrollIntoView({ behavior: 'smooth' })}
          >
            <span>▤</span> Documents
          </button>

          <button
            className="public-nav-item"
            onClick={() => document.getElementById('question-input')?.focus()}
          >
            <span>✧</span> Ask AI
          </button>

          <button className="public-nav-item">
            <span>◉</span> Profile
          </button>
        </div>

        <div className="public-sidebar-section public-sidebar-documents">
          <p className="public-sidebar-heading">YOUR DOCUMENTS</p>

          {documents.length === 0 ? (
            <p className="public-sidebar-empty">No documents available</p>
          ) : (
            documents.slice(0, 5).map((doc, index) => (
              <button
                key={doc.document_id || index}
                className={`public-document-link ${
                  selectedDocument?.document_id === doc.document_id ? 'selected' : ''
                }`}
                onClick={() => setSelectedDocument(doc)}
                title={getFilename(doc)}
              >
                <span>📄</span>
                <span>{getFilename(doc)}</span>
              </button>
            ))
          )}
        </div>

        <div className="public-sidebar-bottom">
          <div className="public-user-card">
            <div className="public-user-avatar">U</div>
            <div>
              <strong>Public User</strong>
              <span>Standard Access</span>
            </div>
          </div>

          <button className="public-logout-button" onClick={handleLogout}>
            ↪ Logout
          </button>
        </div>
      </aside>

      <main className="public-main">
        <header className="public-topbar">
          <div>
            <h1>Knowledge Workspace</h1>
            <p>Explore documents and get answers from your knowledge base.</p>
          </div>

          <button
            className="public-refresh-button"
            onClick={() => fetchDocuments()}
            disabled={documentsLoading}
          >
            ↻ {documentsLoading ? 'Refreshing...' : 'Refresh'}
          </button>
        </header>

        {error && <div className="public-error-banner">{error}</div>}

        <section className="public-stats-grid">
          <div className="public-stat-card">
            <span className="public-stat-icon">▤</span>
            <div>
              <p>Total Documents</p>
              <h2>{documents.length}</h2>
            </div>
          </div>

          <div className="public-stat-card">
            <span className="public-stat-icon">▣</span>
            <div>
              <p>Document Versions</p>
              <h2>{versionCount}</h2>
            </div>
          </div>

          <div className="public-stat-card">
            <span className="public-stat-icon">✧</span>
            <div>
              <p>AI Assistant</p>
              <h2>Online</h2>
            </div>
          </div>
        </section>

        <section className="public-workspace">
          <div className="public-viewer-panel">
            <div className="public-panel-header">
              <div>
                <h2>Document Viewer</h2>
                <p>
                  {selectedDocument
                    ? getFilename(selectedDocument)
                    : 'Select a document to preview'}
                </p>
              </div>
              <span className="public-file-badge">PDF VIEWER</span>
            </div>

            <div className="public-viewer-toolbar">
              <span>Document Preview</span>
              <span>
                {selectedDocument ? getFilename(selectedDocument) : 'No document selected'}
              </span>
            </div>

            <div className="public-pdf-viewer">
              {pdfLoading && (
                <div className="public-viewer-message">
                  <div className="public-loader"></div>
                  <p>Loading document...</p>
                </div>
              )}

              {!pdfLoading && pdfError && (
                <div className="public-viewer-message">
                  <span className="public-empty-icon">📄</span>
                  <h3>Preview unavailable</h3>
                  <p>{pdfError}</p>
                </div>
              )}

              {!pdfLoading && !pdfError && pdfUrl && (
                <iframe
                  title="Document Preview"
                  src={pdfUrl}
                  className="public-pdf-frame"
                />
              )}

              {!pdfLoading && !pdfError && !pdfUrl && !selectedDocument && (
                <div className="public-viewer-message">
                  <span className="public-empty-icon">📂</span>
                  <h3>No document selected</h3>
                  <p>Choose a document from the list to view it here.</p>
                </div>
              )}
            </div>

            <div className="public-document-list" id="your-documents">
              <div className="public-list-heading">
                <div>
                  <h3>Your Documents</h3>
                  <p>Select a document to preview it.</p>
                </div>
                <span>{documents.length} files</span>
              </div>

              {documentsLoading ? (
                <p className="public-list-message">Loading documents...</p>
              ) : documents.length === 0 ? (
                <p className="public-list-message">No documents found.</p>
              ) : (
                <div className="public-document-items">
                  {documents.map((doc, index) => (
                    <button
                      key={doc.document_id || index}
                      className={`public-document-item ${
                        selectedDocument?.document_id === doc.document_id
                          ? 'selected'
                          : ''
                      }`}
                      onClick={() => setSelectedDocument(doc)}
                    >
                      <span className="public-document-icon">📄</span>
                      <span className="public-document-info">
                        <strong>{getFilename(doc)}</strong>
                        <small>
                          {doc.file_type || 'Document'}
                        </small>
                      </span>
                      <span className="public-document-arrow">›</span>
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>

          <aside className="public-assistant-panel">
            <div className="public-assistant-header">
              <div className="public-assistant-avatar">✧</div>
              <div>
                <h2>AI Assistant</h2>
                <span>
                  <i className="public-online-dot"></i> Online
                </span>
              </div>
            </div>

            <div className="public-assistant-intro">
              <div className="public-assistant-welcome-icon">✧</div>
              <h3>Hello! How can I help?</h3>
              <p>
                Ask questions about your uploaded documents.
                I will find relevant information for you.
              </p>
            </div>

            <div className="public-chat-messages">
              {messages.length === 0 && (
                <div className="public-suggestion">
                  <p>Try asking:</p>
                  <button
                    onClick={() => setQuestion('Summarize the selected document')}
                  >
                    Summarize the selected document
                  </button>
                  <button
                    onClick={() => setQuestion('What are the key points?')}
                  >
                    What are the key points?
                  </button>
                </div>
              )}

              {messages.map((message, index) => (
                <div
                  key={index}
                  className={`public-chat-message ${message.type}`}
                >
                  <div className="public-message-label">
                    {message.type === 'user' ? 'You' : 'AI Assistant'}
                  </div>

                  <div className="public-message-content">
                    {message.content}
                  </div>

                  {message.type === 'assistant' &&
                    message.sources?.length > 0 && (
                      <div className="public-sources">
                        <strong>Sources</strong>

                        {message.sources.map((source, sourceIndex) => (
                          <div
                            className="public-source-item"
                            key={sourceIndex}
                          >
                            <span>📄</span>
                            <div>
                              <strong>
                                {source.filename ||
                                  source.file_name ||
                                  source.document_name ||
                                  'Source document'}
                              </strong>
                              <small>
                                {source.page
                                  ? `Page ${source.page}`
                                  : source.section || ''}
                              </small>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}

                  {message.type === 'assistant' && (
                    <small className="public-cache-status">
                      Cache: {message.cacheStatus}
                    </small>
                  )}
                </div>
              ))}

              {chatLoading && (
                <div className="public-thinking">
                  <span className="public-loader small"></span>
                  AI is thinking...
                </div>
              )}
            </div>

            <form className="public-chat-input-area" onSubmit={handleAskQuestion}>
              <textarea
                id="question-input"
                value={question}
                onChange={(event) => setQuestion(event.target.value)}
                placeholder="Ask a question about your documents..."
                rows={3}
                disabled={chatLoading}
              />

              <button
                type="submit"
                disabled={chatLoading || !question.trim()}
              >
                {chatLoading ? 'Thinking...' : 'Send Question  ➤'}
              </button>
            </form>

            <p className="public-assistant-note">
              AI responses are based on your accessible documents.
            </p>
          </aside>
        </section>
      </main>
    </div>
  );
}

export default PublicPage;