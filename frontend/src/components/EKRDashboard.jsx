
import { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import DocumentViewer from './DocumentViewer';
import './EKRDashboard.css';

const API_URL = 'http://127.0.0.1:8000';

function EKRDashboard({ role = 'public' }) {
  const navigate = useNavigate();
  const isAdmin = role === 'admin';

  const [documents, setDocuments] = useState([]);
  const [search, setSearch] = useState('');
  const [selectedDocument, setSelectedDocument] = useState(null);

  const [previewUrl, setPreviewUrl] = useState('');
  const [previewError, setPreviewError] = useState('');
  const [previewLoading, setPreviewLoading] = useState(false);

  const previewRequestRef = useRef(0);
  const previewUrlRef = useRef('');

  const [question, setQuestion] = useState('');
  const [messages, setMessages] = useState([
    {
      role: 'ai',
      text: 'Hello! I am your EKR AI assistant. Ask me anything about the available documents.',
      sources: [],
    },
  ]);

  const [documentsLoading, setDocumentsLoading] = useState(true);
  const [documentsError, setDocumentsError] = useState('');
  const [asking, setAsking] = useState(false);

  const [showUpload, setShowUpload] = useState(false);
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [uploadMessage, setUploadMessage] = useState('');

  const [deletingId, setDeletingId] = useState(null);

  // API headers
  const getHeaders = () => {
    const headers = {};

    if (isAdmin) {
      const key = sessionStorage.getItem('ekr_admin_api_key');
      if (key) headers['X-API-Key'] = key;
    }

    return headers;
  };

  // Preview URL cleanup
  const clearPreviewUrl = () => {
    if (previewUrlRef.current) {
      URL.revokeObjectURL(previewUrlRef.current);
      previewUrlRef.current = '';
    }

    setPreviewUrl('');
  };

  useEffect(() => {
    return () => {
      previewRequestRef.current += 1;

      if (previewUrlRef.current) {
        URL.revokeObjectURL(previewUrlRef.current);
        previewUrlRef.current = '';
      }
    };
  }, []);

  // Fetch documents
  const fetchDocuments = async () => {
    try {
      setDocumentsLoading(true);
      setDocumentsError('');

      const response = await fetch(`${API_URL}/api/documents`, {
        headers: getHeaders(),
      });

      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        throw new Error(data.detail || 'Unable to load documents.');
      }

      const list = Array.isArray(data)
        ? data
        : data.documents || [];

      setDocuments(list);

      setSelectedDocument((current) => {
        if (!current) return null;

        return (
          list.find(
            (doc) => doc.document_id === current.document_id
          ) || null
        );
      });
    } catch (error) {
      setDocumentsError(error.message);
    } finally {
      setDocumentsLoading(false);
    }
  };

  useEffect(() => {
    fetchDocuments();
  }, []);

  // Search documents
  const filteredDocuments = useMemo(() => {
    return documents.filter((doc) =>
      (doc.filename || '')
        .toLowerCase()
        .includes(search.toLowerCase())
    );
  }, [documents, search]);

  // Open document preview
  const openPreview = async (doc) => {
    const requestId = ++previewRequestRef.current;

    setSelectedDocument(doc);
    setPreviewError('');
    setPreviewLoading(true);
    clearPreviewUrl();

    const extension = doc.filename
      ?.split('.')
      .pop()
      ?.toLowerCase();

    if (!['pdf', 'docx'].includes(extension)) {
      setPreviewError(
        'Preview is currently available for PDF and DOCX documents.'
      );
      setPreviewLoading(false);
      return;
    }

    try {
      const response = await fetch(
        `${API_URL}/api/documents/${doc.document_id}/file`,
        {
          headers: getHeaders(),
        }
      );

      if (!response.ok) {
        const data = await response.json().catch(() => ({}));

        throw new Error(
          data.detail || 'Unable to load document.'
        );
      }

      const blob = await response.blob();

      // Ignore outdated preview requests
      if (requestId !== previewRequestRef.current) return;

      const url = URL.createObjectURL(blob);

      previewUrlRef.current = url;
      setPreviewUrl(url);
    } catch (error) {
      if (requestId === previewRequestRef.current) {
        setPreviewError(error.message);
      }
    } finally {
      if (requestId === previewRequestRef.current) {
        setPreviewLoading(false);
      }
    }
  };

  // Ask AI
  const handleAsk = async (event) => {
    event.preventDefault();

    const userQuestion = question.trim();

    if (!userQuestion || asking) return;

    setMessages((previous) => [
      ...previous,
      {
        role: 'user',
        text: userQuestion,
        sources: [],
      },
    ]);

    setQuestion('');
    setAsking(true);

    try {
      const response = await fetch(`${API_URL}/api/ask`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...getHeaders(),
        },
        body: JSON.stringify({
          question: userQuestion,
        }),
      });

      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        throw new Error(
          data.detail || 'Unable to get an answer.'
        );
      }

      setMessages((previous) => [
        ...previous,
        {
          role: 'ai',
          text: data.answer || 'No answer returned.',
          sources: data.sources || [],
          cacheStatus: data.cache_status,
        },
      ]);
    } catch (error) {
      setMessages((previous) => [
        ...previous,
        {
          role: 'ai',
          text: `Error: ${error.message}`,
          sources: [],
        },
      ]);
    } finally {
      setAsking(false);
    }
  };

  // Upload document
  const handleUpload = async (event) => {
    event.preventDefault();

    if (!file || uploading) {
      setUploadMessage('Please select a document.');
      return;
    }

    setUploading(true);
    setUploadMessage('');

    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch(`${API_URL}/api/upload`, {
        method: 'POST',
        headers: getHeaders(),
        body: formData,
      });

      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        throw new Error(data.detail || 'Upload failed.');
      }

      setUploadMessage('Document uploaded successfully.');
      setFile(null);

      await fetchDocuments();
    } catch (error) {
      setUploadMessage(`Upload failed: ${error.message}`);
    } finally {
      setUploading(false);
    }
  };

  // Delete document
  const handleDelete = async (doc) => {
    const confirmed = window.confirm(
      `Are you sure you want to delete "${doc.filename}"?`
    );

    if (!confirmed) return;

    setDeletingId(doc.document_id);

    try {
      const response = await fetch(
        `${API_URL}/api/documents/${doc.document_id}`,
        {
          method: 'DELETE',
          headers: getHeaders(),
        }
      );

      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        throw new Error(
          data.detail || 'Unable to delete document.'
        );
      }

      if (
        selectedDocument?.document_id === doc.document_id
      ) {
        previewRequestRef.current += 1;
        clearPreviewUrl();
        setSelectedDocument(null);
        setPreviewError('');
        setPreviewLoading(false);
      }

      await fetchDocuments();

      alert('Document deleted successfully.');
    } catch (error) {
      alert(error.message);
    } finally {
      setDeletingId(null);
    }
  };

  // Logout
  const handleLogout = () => {
    sessionStorage.removeItem('ekr_admin_api_key');
    navigate('/admin-login');
  };

  // File extension
  const getFileType = (filename = '') =>
    filename.split('.').pop().toUpperCase();

  // Source location
  const getSourceLocation = (source) => {
    const details = [];

    if (source.page_number != null) {
      details.push(`Page ${source.page_number}`);
    }

    if (source.section) {
      details.push(source.section);
    }

    if (source.slide_number != null) {
      details.push(`Slide ${source.slide_number}`);
    }

    if (source.sheet_name) {
      details.push(source.sheet_name);
    }

    if (source.table_number != null) {
      details.push(`Table ${source.table_number}`);
    }

    if (source.chunk != null) {
      details.push(`Chunk ${source.chunk}`);
    }

    return details.join(' • ');
  };

  const latestSources = [...messages]
    .reverse()
    .find(
      (message) =>
        message.role === 'ai' &&
        message.sources?.length
    );

  return (
    <div className="ekr-layout">
      {/* SIDEBAR */}
      <aside className="ekr-sidebar">
        <div className="ekr-brand">
          <div className="ekr-logo">E</div>

          <div>
            <h2>EKR</h2>
            <p>Enterprise Knowledge Retrieval</p>
          </div>
        </div>

        <nav className="ekr-nav">
          <button className="active">
            ⌂ &nbsp; Dashboard
          </button>

          <button
            onClick={() =>
              document
                .getElementById('ekr-documents')
                ?.scrollIntoView({ behavior: 'smooth' })
            }
          >
            ▤ &nbsp; View Documents
          </button>

          <button
            onClick={() =>
              document
                .getElementById('ekr-chat')
                ?.scrollIntoView({ behavior: 'smooth' })
            }
          >
            ✧ &nbsp; Ask Questions
          </button>

          <button
            onClick={() =>
              window.open(`${API_URL}/docs`, '_blank')
            }
          >
            ◉ &nbsp; API Docs
          </button>
        </nav>

        <div className="ekr-sidebar-bottom">
          <p>
            {isAdmin
              ? 'Administrator Access'
              : 'Public Access'}
          </p>

          {isAdmin && (
            <button
              className="ekr-danger-button"
              onClick={handleLogout}
            >
              Logout
            </button>
          )}
        </div>
      </aside>

      {/* MAIN CONTENT */}
      <main className="ekr-main">
        <header className="ekr-header">
          <h2>Document Viewer</h2>

          <div className="ekr-user">
            <div className="ekr-avatar">
              {isAdmin ? 'A' : 'P'}
            </div>

            {isAdmin ? 'Admin' : 'Public User'}
          </div>
        </header>

        <div className="ekr-content">
          <section className="ekr-heading">
            <h1>Knowledge Dashboard</h1>
            <p>
              Explore documents and get answers from your
              knowledge base.
            </p>
          </section>

          <div className="ekr-workspace">
            {/* DOCUMENT LIST */}
            <section
              className="ekr-panel"
              id="ekr-documents"
            >
              <div className="ekr-panel-header">
                <h3>
                  Documents ({documents.length})
                </h3>
              </div>

              <div className="ekr-panel-body">
                {isAdmin && (
                  <button
                    className="ekr-primary-button ekr-upload-button"
                    onClick={() => {
                      setUploadMessage('');
                      setShowUpload(true);
                    }}
                  >
                    + Upload Document
                  </button>
                )}

                <input
                  className="ekr-search"
                  placeholder="Search documents..."
                  value={search}
                  onChange={(event) =>
                    setSearch(event.target.value)
                  }
                />

                {documentsLoading ? (
                  <p className="ekr-muted">
                    Loading documents...
                  </p>
                ) : documentsError ? (
                  <p className="ekr-error">
                    {documentsError}
                  </p>
                ) : (
                  <div className="ekr-document-list">
                    {filteredDocuments.length === 0 ? (
                      <p className="ekr-muted">
                        No documents found.
                      </p>
                    ) : (
                      filteredDocuments.map((doc) => (
                        <div
                          className={`ekr-document-item ${
                            selectedDocument?.document_id ===
                            doc.document_id
                              ? 'selected'
                              : ''
                          }`}
                          key={doc.document_id}
                        >
                          <div className="ekr-document-info">
                            <strong>{doc.filename}</strong>

                            <small>
                              {getFileType(doc.filename)} •{' '}
                              {doc.chunks ?? 0} chunks
                            </small>
                          </div>

                          <button
                            className="ekr-small-button"
                            onClick={() => openPreview(doc)}
                          >
                            View
                          </button>

                          {isAdmin && (
                            <button
                              className="ekr-danger-button"
                              disabled={
                                deletingId === doc.document_id
                              }
                              onClick={() => handleDelete(doc)}
                            >
                              {deletingId === doc.document_id
                                ? '...'
                                : 'Delete'}
                            </button>
                          )}
                        </div>
                      ))
                    )}
                  </div>
                )}

                <button
                  className="ekr-small-button"
                  style={{ marginTop: 14 }}
                  onClick={fetchDocuments}
                  disabled={documentsLoading}
                >
                  Refresh
                </button>
              </div>
            </section>

            {/* DOCUMENT PREVIEW */}
            <section className="ekr-panel ekr-document-preview-panel">
              <div className="ekr-panel-header">
                <h3>Document Preview</h3>
              </div>

              <div className="ekr-panel-body">
                {selectedDocument && (
                  <div className="ekr-preview-tabs">
                    <button className="ekr-preview-tab active">
                      {selectedDocument.filename}
                    </button>
                  </div>
                )}

                <div className="ekr-preview-area">
                  {previewLoading ? (
                    <div className="ekr-preview-status">
                      Loading document...
                    </div>
                  ) : previewError ? (
                    <div className="ekr-preview-status">
                      {previewError}
                    </div>
                  ) : previewUrl && selectedDocument ? (
                    <DocumentViewer
                      fileUrl={previewUrl}
                      fileName={selectedDocument.filename}
                      highlightText=""
                      pageNumber={1}
                    />
                  ) : null}
                </div>

                <div className="ekr-related">
                  <h4>
                    Related Information From Documents
                  </h4>

                  {latestSources?.sources?.length ? (
                    latestSources.sources.map(
                      (source, index) => (
                        <div
                          className="ekr-source-card"
                          key={index}
                        >
                          <strong>
                            {source.document ||
                              source.filename ||
                              'Source document'}
                          </strong>

                          <small>
                            {getSourceLocation(source) ||
                              'Source location unavailable'}
                          </small>

                          {source.text && (
                            <p>{source.text}</p>
                          )}
                        </div>
                      )
                    )
                  ) : (
                    <p className="ekr-muted">
                      Ask a question to see related document
                      sources here.
                    </p>
                  )}
                </div>
              </div>
            </section>

            {/* AI CHAT */}
            <section
              className="ekr-panel ekr-chat-panel"
              id="ekr-chat"
            >
              <div className="ekr-panel-header">
                <h3>Ask me a question</h3>
                <div className="ekr-chat-status">
                  ● Online
                </div>
              </div>

              <div className="ekr-chat-messages">
                {messages.map((message, index) => (
                  <div
                    className={`ekr-message ${message.role}`}
                    key={index}
                  >
                    {message.text}

                    {message.sources?.length > 0 && (
                      <div style={{ marginTop: 10 }}>
                        <strong>
                          Sources ({message.sources.length})
                        </strong>

                        {message.sources.map(
                          (source, sourceIndex) => (
                            <div
                              key={sourceIndex}
                              style={{ marginTop: 8 }}
                            >
                              <small>
                                {source.document ||
                                  source.filename ||
                                  'Document'}

                                {getSourceLocation(source)
                                  ? ` — ${getSourceLocation(source)}`
                                  : ''}
                              </small>
                            </div>
                          )
                        )}
                      </div>
                    )}
                  </div>
                ))}

                {asking && (
                  <div className="ekr-message ai">
                    Searching documents... Please wait.
                  </div>
                )}
              </div>

              <form
                className="ekr-chat-form"
                onSubmit={handleAsk}
              >
                <input
                  className="ekr-question-input"
                  placeholder="Type your question..."
                  value={question}
                  onChange={(event) =>
                    setQuestion(event.target.value)
                  }
                  disabled={asking}
                />

                <button
                  className="ekr-primary-button"
                  type="submit"
                  disabled={!question.trim() || asking}
                >
                  Send
                </button>
              </form>
            </section>
          </div>
        </div>
      </main>

      {/* ADMIN UPLOAD MODAL */}
      {showUpload && isAdmin && (
        <div className="ekr-modal-overlay">
          <div className="ekr-modal">
            <h2>Upload Document</h2>

            <p>
              Select a document to add to the knowledge base.
            </p>

            <form onSubmit={handleUpload}>
              <input
                type="file"
                accept=".pdf,.docx,.doc,.xlsx,.xls,.html,.htm,.csv,.txt,.md,.pptx"
                onChange={(event) =>
                  setFile(event.target.files?.[0] || null)
                }
              />

              {uploadMessage && (
                <p>{uploadMessage}</p>
              )}

              <div className="ekr-modal-actions">
                <button
                  type="button"
                  className="ekr-danger-button"
                  onClick={() => {
                    setShowUpload(false);
                    setFile(null);
                    setUploadMessage('');
                  }}
                >
                  Cancel
                </button>

                <button
                  type="submit"
                  className="ekr-primary-button"
                  disabled={uploading}
                >
                  {uploading ? 'Uploading...' : 'Upload'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

export default EKRDashboard;
