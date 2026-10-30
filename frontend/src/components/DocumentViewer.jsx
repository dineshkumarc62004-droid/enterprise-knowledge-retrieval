
import { useEffect, useRef, useState } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import { renderAsync } from 'docx-preview';

import './DocumentViewer.css';
import 'react-pdf/dist/Page/TextLayer.css';
import 'react-pdf/dist/Page/AnnotationLayer.css';

pdfjs.GlobalWorkerOptions.workerSrc = new URL(
  'pdfjs-dist/build/pdf.worker.min.mjs',
  import.meta.url
).toString();

export default function DocumentViewer({
  fileUrl,
  fileName,
  highlightText = '',
  pageNumber = 1,
  onClose,
}) {
  const [fileType, setFileType] = useState('');
  const [pdfPages, setPdfPages] = useState(0);
  const [pdfWidth, setPdfWidth] = useState(500);
  const [currentPage, setCurrentPage] = useState(1);
  const [zoom, setZoom] = useState(100);

  const [pdfError, setPdfError] = useState('');
  const [docxError, setDocxError] = useState('');
  const [loading, setLoading] = useState(false);

  const docxContainerRef = useRef(null);
  const viewerContentRef = useRef(null);
  const docxRequestRef = useRef(0);

  function normalizeText(value) {
    return (value || '')
      .replace(/\s+/g, ' ')
      .trim()
      .toLowerCase();
  }

  // Detect file type and reset preview
  useEffect(() => {
    const extension = fileName?.split('.').pop()?.toLowerCase();

    setFileType(extension || '');
    setPdfPages(0);
    setCurrentPage(Number(pageNumber) || 1);
    setZoom(100);
    setPdfError('');
    setDocxError('');
    setLoading(false);
  }, [fileName, fileUrl]);

  // Automatically fit PDF to preview container
  useEffect(() => {
    if (fileType !== 'pdf') return;

    const container = viewerContentRef.current;

    if (!container) return;

    let animationFrame;

    const updatePdfWidth = () => {
      cancelAnimationFrame(animationFrame);

      animationFrame = requestAnimationFrame(() => {
        const availableWidth = Math.floor(
          container.clientWidth - 32
        );

        if (availableWidth > 0) {
          setPdfWidth(availableWidth);
        }
      });
    };

    updatePdfWidth();

    const resizeObserver = new ResizeObserver(() => {
      updatePdfWidth();
    });

    resizeObserver.observe(container);

    window.addEventListener('resize', updatePdfWidth);

    return () => {
      cancelAnimationFrame(animationFrame);
      resizeObserver.disconnect();
      window.removeEventListener('resize', updatePdfWidth);
    };
  }, [fileType, fileUrl]);

  // Load DOCX document safely
  useEffect(() => {
    if (fileType !== 'docx' || !fileUrl) return;

    const requestId = ++docxRequestRef.current;
    let cancelled = false;

    async function loadDocx() {
      try {
        setLoading(true);
        setDocxError('');

        if (docxContainerRef.current) {
          docxContainerRef.current.innerHTML = '';
        }

        const response = await fetch(fileUrl);

        if (!response.ok) {
          throw new Error('Unable to load DOCX document.');
        }

        const blob = await response.blob();

        if (
          cancelled ||
          requestId !== docxRequestRef.current ||
          !docxContainerRef.current
        ) {
          return;
        }

        await renderAsync(
          blob,
          docxContainerRef.current,
          docxContainerRef.current,
          {
            className: 'docx-viewer',
            inWrapper: true,
            ignoreWidth: false,
            ignoreHeight: false,
            breakPages: true,
          }
        );

        if (
          cancelled ||
          requestId !== docxRequestRef.current
        ) {
          return;
        }

        if (highlightText) {
          highlightDocxText(
            docxContainerRef.current,
            highlightText
          );
        }
      } catch (error) {
        if (!cancelled) {
          setDocxError(error.message);
        }
      } finally {
        if (
          !cancelled &&
          requestId === docxRequestRef.current
        ) {
          setLoading(false);
        }
      }
    }

    loadDocx();

    return () => {
      cancelled = true;
      docxRequestRef.current += 1;
    };
  }, [fileType, fileUrl, highlightText]);

  // Highlight matching DOCX paragraph or table cell
  function highlightDocxText(container, searchText) {
    const target = normalizeText(searchText);

    if (!target) return;

    const targetWords = new Set(
      target.split(' ').filter((word) => word.length > 2)
    );

    const elements = container.querySelectorAll(
      'p, table td, table th'
    );

    let bestElement = null;
    let bestScore = 0;

    elements.forEach((element) => {
      element.classList.remove('document-highlight');

      const content = normalizeText(element.textContent);

      if (!content) return;

      if (content.includes(target)) {
        bestElement = element;
        bestScore = Number.MAX_SAFE_INTEGER;
        return;
      }

      if (bestScore === Number.MAX_SAFE_INTEGER) return;

      const elementWords = new Set(content.split(' '));
      let matches = 0;

      targetWords.forEach((word) => {
        if (elementWords.has(word)) {
          matches += 1;
        }
      });

      const score =
        matches / Math.max(targetWords.size, 1);

      if (score > bestScore) {
        bestScore = score;
        bestElement = element;
      }
    });

    if (bestElement && bestScore >= 0.15) {
      bestElement.classList.add('document-highlight');

      bestElement.scrollIntoView({
        behavior: 'smooth',
        block: 'center',
      });
    }
  }

  // Navigate to selected PDF page
  useEffect(() => {
    if (fileType !== 'pdf' || !pdfPages) return;

    const validPage = Math.min(
      Math.max(Number(pageNumber) || 1, 1),
      pdfPages
    );

    setCurrentPage(validPage);

    const timer = setTimeout(() => {
      const pageElement = document.getElementById(
        `pdf-page-${validPage}`
      );

      pageElement?.scrollIntoView({
        behavior: 'smooth',
        block: 'start',
      });
    }, 300);

    return () => clearTimeout(timer);
  }, [fileType, pdfPages, pageNumber, highlightText]);

  // PDF load success
  function handlePdfLoadSuccess({ numPages }) {
    setPdfPages(numPages);
    setCurrentPage(1);
    setPdfError('');
  }

  // PDF load error
  function handlePdfLoadError() {
    setPdfError('Unable to load PDF document.');
  }

  // PDF page navigation
  function goToPage(page) {
    const nextPage = Math.min(
      Math.max(Number(page), 1),
      pdfPages
    );

    setCurrentPage(nextPage);

    document
      .getElementById(`pdf-page-${nextPage}`)
      ?.scrollIntoView({
        behavior: 'smooth',
        block: 'start',
      });
  }

  // PDF zoom controls
  function zoomIn() {
    setZoom((previous) => Math.min(previous + 10, 150));
  }

  function zoomOut() {
    setZoom((previous) => Math.max(previous - 10, 50));
  }

  function resetZoom() {
    setZoom(100);
  }

  // Highlight matching PDF text
  function renderPdfText({ str }) {
    if (!highlightText || !str) return str;

    const target = normalizeText(highlightText);
    const current = normalizeText(str);

    if (current.length > 2 && target.includes(current)) {
      return (
        <mark className="pdf-text-highlight">
          {str}
        </mark>
      );
    }

    return str;
  }

  if (!fileUrl) {
    return null;
  }

  return (
    <div className="document-viewer">

      {/* DOCUMENT HEADER */}
      <div className="document-viewer-header">
        <div className="document-viewer-title">
          <strong>{fileName || 'Document Preview'}</strong>
          <span>{fileType.toUpperCase()} Document</span>
        </div>

        {onClose && (
          <button
            type="button"
            onClick={onClose}
            className="document-viewer-close"
          >
            Close
          </button>
        )}
      </div>

      {/* PDF TOOLBAR */}
      {fileType === 'pdf' && (
        <div className="document-viewer-toolbar">

          <div className="pdf-page-controls">
            <button
              type="button"
              onClick={() => goToPage(currentPage - 1)}
              disabled={currentPage <= 1}
              title="Previous page"
            >
              ◀
            </button>

            <span>
              <input
                type="number"
                min="1"
                max={pdfPages || 1}
                value={currentPage}
                onChange={(event) => {
                  const value = Number(event.target.value);

                  if (
                    value >= 1 &&
                    value <= pdfPages
                  ) {
                    goToPage(value);
                  }
                }}
                aria-label="Page number"
              />

              {' / '}

              {pdfPages || '--'}
            </span>

            <button
              type="button"
              onClick={() => goToPage(currentPage + 1)}
              disabled={
                !pdfPages || currentPage >= pdfPages
              }
              title="Next page"
            >
              ▶
            </button>
          </div>

          <div className="pdf-zoom-controls">
            <button
              type="button"
              onClick={zoomOut}
              disabled={zoom <= 50}
              title="Zoom out"
            >
              −
            </button>

            <button
              type="button"
              onClick={resetZoom}
              title="Reset zoom"
            >
              {zoom}%
            </button>

            <button
              type="button"
              onClick={zoomIn}
              disabled={zoom >= 150}
              title="Zoom in"
            >
              +
            </button>
          </div>
        </div>
      )}

      {/* DOCUMENT CONTENT */}
      <div
        className="document-viewer-content"
        ref={viewerContentRef}
      >

        {/* PDF PREVIEW */}
        {fileType === 'pdf' && (
          <div className="pdf-document">
            <Document
              file={fileUrl}
              onLoadSuccess={handlePdfLoadSuccess}
              onLoadError={handlePdfLoadError}
              loading="Loading PDF..."
              error={pdfError}
            >
              {pdfPages > 0 &&
                Array.from(
                  { length: pdfPages },
                  (_, index) => (
                    <div
                      key={index}
                      id={`pdf-page-${index + 1}`}
                      className={`pdf-page-wrapper ${
                        currentPage === index + 1
                          ? 'pdf-target-page'
                          : ''
                      }`}
                    >
                      <Page
                        pageNumber={index + 1}
                        renderTextLayer
                        renderAnnotationLayer={false}
                        textRenderer={renderPdfText}
                        width={Math.max(
                          100,
                          Math.floor(
                            pdfWidth * (zoom / 100)
                          )
                        )}
                      />
                    </div>
                  )
                )}
            </Document>
          </div>
        )}

        {/* DOCX PREVIEW */}
        {fileType === 'docx' && (
          <div className="docx-document">
            {loading && (
              <p className="document-viewer-loading">
                Loading DOCX...
              </p>
            )}

            {docxError && (
              <p className="document-viewer-error">
                {docxError}
              </p>
            )}

            <div ref={docxContainerRef} />
          </div>
        )}

        {/* UNSUPPORTED FILE */}
        {!['pdf', 'docx'].includes(fileType) && (
          <div className="document-viewer-empty">
            Preview is currently supported for PDF and DOCX files.
          </div>
        )}
      </div>
    </div>
  );
}
