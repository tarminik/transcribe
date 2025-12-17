import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

const API_BASE = (import.meta.env.VITE_API_BASE ?? '/api').replace(/\/$/, '');
const BACKEND_ORIGIN = (import.meta.env.VITE_BACKEND_ORIGIN ?? 'http://localhost:8000').replace(/\/$/, '');

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

const parsePositiveInt = (value) => {
  if (value == null) return null;
  const parsed = Number.parseInt(value, 10);
  if (!Number.isFinite(parsed) || parsed <= 0) {
    return null;
  }
  return parsed;
};

const TRANSCRIPTION_POLL_INTERVAL_MS = 2000;
const TRANSCRIPTION_MAX_WAIT_MS =
  parsePositiveInt(import.meta.env.VITE_TRANSCRIPTION_MAX_WAIT_MS) ?? 10 * 60 * 1000;

const LANGUAGE_OPTIONS = [
  { value: 'auto', label: 'Auto detect' },
  { value: 'en', label: 'English (en)' },
  { value: 'ru', label: 'Russian (ru)' },
  { value: 'es', label: 'Spanish (es)' },
  { value: 'de', label: 'German (de)' },
  { value: 'fr', label: 'French (fr)' },
  { value: 'it', label: 'Italian (it)' },
  { value: 'pt', label: 'Portuguese (pt)' },
  { value: 'hi', label: 'Hindi (hi)' },
  { value: 'zh', label: 'Chinese Mandarin (zh)' },
  { value: 'ja', label: 'Japanese (ja)' },
];

const joinPath = (base, path) => {
  if (!path.startsWith('/')) {
    return `${base}/${path}`;
  }
  if (base === '') return path;
  return `${base}${path}`;
};

const buildApiUrl = (path) => {
  if (path.startsWith('http')) return path;
  if (API_BASE.startsWith('http')) {
    return `${API_BASE}${path}`;
  }
  return joinPath(API_BASE, path);
};

const isBackendUrl = (url) => {
  if (url.startsWith('/')) {
    return true;
  }
  try {
    const target = new URL(url, window.location.origin);
    const backend = new URL(BACKEND_ORIGIN, window.location.origin);
    return target.origin === backend.origin;
  } catch (err) {
    console.error('Invalid URL provided', url, err);
    return false;
  }
};

const toProxyUrl = (url) => {
  if (API_BASE.startsWith('http')) {
    return url;
  }
  try {
    const parsed = new URL(url, BACKEND_ORIGIN);
    return `${API_BASE}${parsed.pathname}${parsed.search}`;
  } catch (err) {
    return url;
  }
};

function App() {
  const TOKEN_STORAGE_KEY = 'transcribe_token';
  const [token, setToken] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [authError, setAuthError] = useState('');
  const [authSuccess, setAuthSuccess] = useState('');
  const [isAuthLoading, setAuthLoading] = useState(false);
  const [authMode, setAuthMode] = useState('login');

  const [selectedFile, setSelectedFile] = useState(null);
  const [language, setLanguage] = useState('auto');
  const [mode, setMode] = useState('mono');
  const [isSubmitting, setSubmitting] = useState(false);
  const [statusMessage, setStatusMessage] = useState('');
  const [resultText, setResultText] = useState('');
  const [resultFilename, setResultFilename] = useState('');
  const [jobStatus, setJobStatus] = useState(null);
  const [historyItems, setHistoryItems] = useState([]);
  const [historyError, setHistoryError] = useState('');
  const [isHistoryLoading, setHistoryLoading] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef(null);

  const hasAsideContent = Boolean(statusMessage || jobStatus || resultText);

  const isAuthenticated = useMemo(() => Boolean(token), [token]);

  // Restore token on first load.
  useEffect(() => {
    const savedToken = localStorage.getItem(TOKEN_STORAGE_KEY);
    if (savedToken) {
      setToken(savedToken);
    }
  }, []);

  // Persist or clear token when it changes.
  useEffect(() => {
    if (token) {
      localStorage.setItem(TOKEN_STORAGE_KEY, token);
    } else {
      localStorage.removeItem(TOKEN_STORAGE_KEY);
    }
  }, [token]);

  useEffect(() => {
    fetchHistory();
  }, [fetchHistory]);

  const apiFetch = useCallback(
    async (path, options = {}) => {
      const url = buildApiUrl(path);
      const headers = new Headers(options.headers || {});
      if (token) {
        headers.set('Authorization', `Bearer ${token}`);
      }
      const init = {
        credentials: API_BASE.startsWith('http') ? 'include' : 'same-origin',
        ...options,
        headers,
      };
      const response = await fetch(url, init);
      if (!response.ok) {
        const cloned = response.clone();
        let body;
        try {
          body = await response.json();
        } catch (err) {
          body = await cloned.text();
        }
        const error = new Error(body?.detail ?? response.statusText);
        error.status = response.status;
        throw error;
      }
      return response;
    },
    [token]
  );

  const fetchHistory = useCallback(async () => {
    if (!token) {
      setHistoryItems([]);
      setHistoryError('');
      return;
    }

    setHistoryLoading(true);
    setHistoryError('');
    try {
      const response = await apiFetch('/history/', { method: 'GET' });
      const data = await response.json();
      setHistoryItems(data);
    } catch (error) {
      setHistoryError(error.message || 'Failed to load history.');
    } finally {
      setHistoryLoading(false);
    }
  }, [apiFetch, token]);

  const performLogin = useCallback(
    async (emailValue, passwordValue) => {
      const params = new URLSearchParams();
      params.set('username', emailValue.trim());
      params.set('password', passwordValue);
      const response = await apiFetch('/auth/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: params.toString(),
      });
      const data = await response.json();
      setToken(data.access_token);
    },
    [apiFetch]
  );

  const handleLogin = async (event) => {
    event.preventDefault();
    setAuthError('');
    setAuthSuccess('');
    setAuthLoading(true);
    try {
      await performLogin(email, password);
    } catch (error) {
      setAuthError(error.message || 'Login failed');
    } finally {
      setAuthLoading(false);
    }
  };

  const handleRegister = async (event) => {
    event.preventDefault();
    setAuthError('');
    setAuthSuccess('');
    setAuthLoading(true);

    if (password.length < 8) {
      setAuthError('Password must be at least 8 characters.');
      setAuthLoading(false);
      return;
    }

    try {
      const response = await apiFetch('/auth/register', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email: email.trim(),
          password,
        }),
      });

      if (!response.ok) {
        const errorBody = await response.json();
        throw new Error(errorBody?.detail || 'Registration failed');
      }

      await performLogin(email, password);
      setAuthSuccess('Account created and you are now signed in.');
    } catch (error) {
      setAuthError(error.message || 'Registration failed');
    } finally {
      setAuthLoading(false);
    }
  };

  const uploadToStorage = useCallback(
    async (uploadUrl, file) => {
      const headers = new Headers();
      const contentType = file.type || 'application/octet-stream';
      headers.set('Content-Type', contentType);

      let targetUrl = uploadUrl;
      if (isBackendUrl(uploadUrl)) {
        headers.set('Authorization', `Bearer ${token}`);
        targetUrl = toProxyUrl(uploadUrl);
      }

      const response = await fetch(targetUrl, {
        method: 'PUT',
        headers,
        body: file,
      });

      if (!response.ok) {
        if (response.status === 413) {
          throw new Error('Upload failed: file is too large for the server limit.');
        }
        throw new Error(`Upload failed (${response.status})`);
      }
    },
    [token]
  );

  const downloadTranscript = useCallback(
    async (jobId) => {
      const response = await apiFetch(`/jobs/${jobId}/download`, {
        method: 'GET',
      });
      const { download_url: downloadUrl } = await response.json();

      let targetUrl = downloadUrl;
      const headers = new Headers();
      if (isBackendUrl(downloadUrl)) {
        headers.set('Authorization', `Bearer ${token}`);
        targetUrl = toProxyUrl(downloadUrl);
      }

      const fileResponse = await fetch(targetUrl, {
        method: 'GET',
        headers,
      });
      if (!fileResponse.ok) {
        throw new Error('Failed to fetch transcript');
      }
      const text = await fileResponse.text();
      setResultText(text);
      setResultFilename(`transcript-${jobId}.txt`);
      return text;
    },
    [apiFetch, token]
  );

  const monitorJob = useCallback(
    async (jobId) => {
      setStatusMessage('Processing transcription...');
      const start = Date.now();
      let hasWarnedAboutDelay = false;
      // Continue polling until the job finishes; emit a friendlier message once it runs long.
      for (;;) {
        const response = await apiFetch(`/jobs/${jobId}`, { method: 'GET' });
        const jobData = await response.json();
        setJobStatus(jobData);

        if (jobData.status === 'completed') {
          await downloadTranscript(jobId);
          setStatusMessage('Transcription ready!');
          await fetchHistory();
          return;
        }
        if (jobData.status === 'failed') {
          setStatusMessage(jobData.error_message || 'Transcription failed.');
          return;
        }
        if (!hasWarnedAboutDelay && Date.now() - start > TRANSCRIPTION_MAX_WAIT_MS) {
          setStatusMessage(
            'Transcription is still processing. Keep this page open and we will refresh once it is ready.'
          );
          hasWarnedAboutDelay = true;
        }

        await sleep(TRANSCRIPTION_POLL_INTERVAL_MS);
      }
    },
    [apiFetch, downloadTranscript, fetchHistory]
  );

  const openHistoryEntry = useCallback(
    async (historyId) => {
      setStatusMessage('Loading transcript...');
      try {
        const response = await apiFetch(`/history/${historyId}`, { method: 'GET' });
        const data = await response.json();
        setResultText(data.transcript_text);
        const safeTitle = (data.title || '').trim();
        const filenameBase = safeTitle || `transcript-${data.job_id}`;
        setResultFilename(`${filenameBase}.txt`);
        setJobStatus(null);
        setStatusMessage(`Showing transcript${safeTitle ? `: ${safeTitle}` : ''}.`);
      } catch (error) {
        setStatusMessage(error.message || 'Unable to load transcript from history.');
      }
    },
    [apiFetch]
  );

  const handleTranscribe = async (event) => {
    event.preventDefault();
    if (!selectedFile) {
      setStatusMessage('Please choose a file.');
      return;
    }

    setSubmitting(true);
    setStatusMessage('Requesting upload URL...');
    setResultText('');
    setResultFilename('');
    setJobStatus(null);

    try {
      const presignResponse = await apiFetch('/files/presign', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          filename: selectedFile.name,
          content_type: selectedFile.type || 'application/octet-stream',
        }),
      });
      const { upload_url: uploadUrl, object_key: objectKey } = await presignResponse.json();

      setStatusMessage('Uploading file...');
      await uploadToStorage(uploadUrl, selectedFile);

      setStatusMessage('Creating transcription job...');
      const jobResponse = await apiFetch('/jobs/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          object_key: objectKey,
          language,
          mode,
        }),
      });
      const job = await jobResponse.json();
      setJobStatus(job);
      await monitorJob(job.id);
    } catch (error) {
      console.error(error);
      setStatusMessage(error.message || 'Something went wrong.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDownloadClick = () => {
    if (!resultText || !resultFilename) return;
    const blob = new Blob([resultText], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = resultFilename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  };

  const handleLogout = () => {
    setToken('');
    setEmail('');
    setPassword('');
    setSelectedFile(null);
    setResultText('');
    setResultFilename('');
    setJobStatus(null);
    setStatusMessage('');
    setHistoryItems([]);
    setHistoryError('');
    setHistoryLoading(false);
  };

  const handleDragOver = (event) => {
    event.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (event) => {
    event.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (event) => {
    event.preventDefault();
    setIsDragging(false);
    const files = event.dataTransfer.files;
    if (files.length > 0) {
      setSelectedFile(files[0]);
    }
  };

  const handleFileChange = (event) => {
    const files = event.target.files;
    if (files && files.length > 0) {
      setSelectedFile(files[0]);
    }
  };

  const handleDropzoneKeyDown = (event) => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      fileInputRef.current?.click();
    }
  };

  const authenticatedCardClass = `card card--workspace${
    hasAsideContent ? ' card--workspace--with-aside' : ''
  }`;

  return (
    <div className="page">
      <header className="page__header">
        <h1>Transcribe</h1>
        {isAuthenticated && (
          <button type="button" className="link-button" onClick={handleLogout}>
            Log out
          </button>
        )}
      </header>

      {!isAuthenticated ? (
        <main className="card card--auth">
          <div className="auth-toggle">
            <button
              type="button"
              className={authMode === 'login' ? 'auth-toggle__btn is-active' : 'auth-toggle__btn'}
              onClick={() => {
                setAuthMode('login');
                setAuthError('');
                setAuthSuccess('');
              }}
              aria-pressed={authMode === 'login'}
            >
              Sign in
            </button>
            <button
              type="button"
              className={authMode === 'register' ? 'auth-toggle__btn is-active' : 'auth-toggle__btn'}
              onClick={() => {
                setAuthMode('register');
                setAuthError('');
                setAuthSuccess('');
              }}
              aria-pressed={authMode === 'register'}
            >
              Create account
            </button>
          </div>
          <h2>{authMode === 'login' ? 'Sign in' : 'Create account'}</h2>
          <p className="hint">
            {authMode === 'login'
              ? 'Use your existing email and password to continue.'
              : 'Create a new account with email and password (minimum 8 characters).'}
          </p>
          <form className="form" onSubmit={authMode === 'login' ? handleLogin : handleRegister}>
            <label className="field">
              <span>Email</span>
              <input
                type="email"
                required
                autoComplete="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
              />
            </label>
            <label className="field">
              <span>Password</span>
              <input
                type="password"
                required
                autoComplete="current-password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
              />
            </label>
            {authError && <div className="error">{authError}</div>}
            {authSuccess && <div className="status status--inline">{authSuccess}</div>}
            <button type="submit" className="primary" disabled={isAuthLoading}>
              {isAuthLoading && <span className="loading-spinner"></span>}
              {authMode === 'login'
                ? isAuthLoading
                  ? 'Signing in…'
                  : 'Sign in'
                : isAuthLoading
                  ? 'Creating account…'
                  : 'Create account'}
            </button>
          </form>
        </main>
      ) : (
        <main className={authenticatedCardClass}>
          <h2>Transcribe audio or video</h2>
          <form className="form" onSubmit={handleTranscribe}>
            <div className="field">
              <span>Choose file</span>
              <div
                className={`file-upload-area${isDragging ? ' drag-over' : ''}`}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
                onKeyDown={handleDropzoneKeyDown}
                tabIndex={0}
                role="button"
                aria-label="Upload audio or video file"
              >
                <div className="file-upload-area__icon">📁</div>
                <div className="file-upload-area__text">
                  {selectedFile ? 'Click or drag to change file' : 'Click or drag file here'}
                </div>
                <div className="file-upload-area__hint">
                  {selectedFile ? '' : 'Supports audio and video files'}
                </div>
                {selectedFile && (
                  <div className="file-upload-area__selected">{selectedFile.name}</div>
                )}
              </div>
              <input
                id="file-input"
                ref={fileInputRef}
                type="file"
                required
                onChange={handleFileChange}
                style={{
                  position: 'absolute',
                  opacity: 0,
                  width: 1,
                  height: 1,
                  pointerEvents: 'none',
                }}
              />
            </div>
            <label className="field">
              <span>Language</span>
              <select value={language} onChange={(event) => setLanguage(event.target.value)}>
                {LANGUAGE_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
            <div className="field">
              <span>Speaker mode</span>
              <div className="field__options">
                <label>
                  <input
                    type="radio"
                    name="mode"
                    value="mono"
                    checked={mode === 'mono'}
                    onChange={(event) => setMode(event.target.value)}
                  />
                  Mono
                </label>
                <label>
                  <input
                    type="radio"
                    name="mode"
                    value="dialogue"
                    checked={mode === 'dialogue'}
                    onChange={(event) => setMode(event.target.value)}
                  />
                  Dialogue
                </label>
                <label>
                  <input
                    type="radio"
                    name="mode"
                    value="multi"
                    checked={mode === 'multi'}
                    onChange={(event) => setMode(event.target.value)}
                  />
                  Multiple
                </label>
              </div>
            </div>
            <button type="submit" className="primary" disabled={isSubmitting}>
              {isSubmitting && <span className="loading-spinner"></span>}
              {isSubmitting ? 'Processing…' : 'Transcribe'}
            </button>
          </form>
          <aside className="workspace__aside">
            {statusMessage && (
              <div className="status">
                {statusMessage}
                {isSubmitting && <div className="progress-bar"><div className="progress-bar__fill"></div></div>}
              </div>
            )}

            {jobStatus && (
              <div className="job-status">
                <div>
                  <strong>Status:</strong>
                  <span className={`job-status-badge job-status-badge--${jobStatus.status}`}>
                    {jobStatus.status === 'pending' && '⏱️'}
                    {jobStatus.status === 'processing' && '⚙️'}
                    {jobStatus.status === 'completed' && '✅'}
                    {jobStatus.status === 'failed' && '❌'}
                    {' '}
                    {jobStatus.status}
                  </span>
                </div>
                {jobStatus.error_message && <div>Error: {jobStatus.error_message}</div>}
              </div>
            )}

            {resultText && (
              <div className="result">
                <h3>Transcript</h3>
                <pre className="result__preview">{resultText}</pre>
                <button type="button" onClick={handleDownloadClick}>
                  Download TXT
                </button>
              </div>
            )}
          </aside>

          <section className="history">
            <div className="history__header">
              <h3>History</h3>
              <button
                type="button"
                className="history__refresh"
                onClick={fetchHistory}
                disabled={isHistoryLoading}
              >
                {isHistoryLoading ? 'Refreshing…' : 'Refresh'}
              </button>
            </div>

            {historyError && <div className="error">{historyError}</div>}
            {isHistoryLoading && <div className="status status--inline">Loading history…</div>}
            {!isHistoryLoading && historyItems.length === 0 && !historyError && (
              <p className="hint">No completed transcriptions yet. Submit a file to see it here.</p>
            )}

            {historyItems.length > 0 && (
              <ul className="history__list" aria-label="Transcription history">
                {historyItems.map((item) => (
                  <li key={item.id} className="history__item">
                    <div className="history__item-text">
                      <div className="history__title">
                        {item.title || 'Untitled transcription'}
                      </div>
                      <div className="history__meta">
                        {new Date(item.created_at).toLocaleString()}
                      </div>
                    </div>
                    <button
                      type="button"
                      className="history__open"
                      onClick={() => openHistoryEntry(item.id)}
                    >
                      Open
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </main>
      )}

      <footer className="page__footer">
        <small>Backend URL: {API_BASE.startsWith('http') ? API_BASE : BACKEND_ORIGIN}</small>
      </footer>
    </div>
  );
}

export default App;
