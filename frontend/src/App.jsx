import { useCallback, useMemo, useState } from 'react';

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
  const [token, setToken] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [authError, setAuthError] = useState('');
  const [isAuthLoading, setAuthLoading] = useState(false);

  const [selectedFile, setSelectedFile] = useState(null);
  const [language, setLanguage] = useState('ru');
  const [mode, setMode] = useState('mono');
  const [isSubmitting, setSubmitting] = useState(false);
  const [statusMessage, setStatusMessage] = useState('');
  const [resultText, setResultText] = useState('');
  const [resultFilename, setResultFilename] = useState('');
  const [jobStatus, setJobStatus] = useState(null);

  const hasAsideContent = Boolean(statusMessage || jobStatus || resultText);

  const isAuthenticated = useMemo(() => Boolean(token), [token]);

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

  const handleLogin = async (event) => {
    event.preventDefault();
    setAuthError('');
    setAuthLoading(true);
    try {
      const params = new URLSearchParams();
      params.set('username', email.trim());
      params.set('password', password);
      const response = await apiFetch('/auth/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: params.toString(),
      });
      const data = await response.json();
      setToken(data.access_token);
    } catch (error) {
      setAuthError(error.message || 'Login failed');
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
    [apiFetch, downloadTranscript]
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
          <h2>Sign in</h2>
          <p className="hint">Use the same credentials you created via the API.</p>
          <form className="form" onSubmit={handleLogin}>
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
            <button type="submit" className="primary" disabled={isAuthLoading}>
              {isAuthLoading ? 'Signing in…' : 'Sign in'}
            </button>
          </form>
        </main>
      ) : (
        <main className={authenticatedCardClass}>
          <h2>Transcribe audio or video</h2>
          <form className="form" onSubmit={handleTranscribe}>
            <label className="field">
              <span>Choose file</span>
              <input
                type="file"
                required
                onChange={(event) => setSelectedFile(event.target.files?.[0] ?? null)}
              />
            </label>
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
              </div>
            </div>
            <button type="submit" className="primary" disabled={isSubmitting}>
              {isSubmitting ? 'Processing…' : 'Transcribe'}
            </button>
          </form>
          <aside className="workspace__aside">
            {statusMessage && <div className="status">{statusMessage}</div>}

            {jobStatus && (
              <div className="job-status">
                <div>
                  <strong>Job status:</strong> {jobStatus.status}
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
        </main>
      )}

      <footer className="page__footer">
        <small>Backend URL: {API_BASE.startsWith('http') ? API_BASE : BACKEND_ORIGIN}</small>
      </footer>
    </div>
  );
}

export default App;
