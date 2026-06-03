"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Activity,
  BookOpen,
  CheckCircle2,
  CircleAlert,
  Download,
  Loader2,
  Pause,
  Play,
  RefreshCw,
  Sparkles,
  Upload,
  Volume2,
  Waves
} from "lucide-react";
import {
  chapterAudioUrl,
  createChapterJob,
  createJob,
  fetchChapterJob,
  fetchHealth,
  fetchJob,
  fetchModelVoices,
  fetchModels,
  fetchRuntime,
  jobAudioUrl,
  openChapterJobSocket,
  openJobSocket,
  type ChapterJobRecord,
  type JobEvent,
  type JobRecord,
  type JobStatus,
  type ModelInfo,
  type RuntimeInfo,
  type VoiceInfo
} from "@/lib/vieneu-api";
import { useLocalStorageState } from "@/lib/use-local-storage";
import { ServiceWorkerRegister } from "@/components/service-worker-register";

const DEFAULT_TEXT =
  "Xin chao, day la VieNeu Studio.\n\nDay la giao dien chay Text-to-Speech voi may chu VieNeu TTS cuc bo.\nHo tro tieng Viet tu nhien, bieu cam va chuan ngu dieu.\n\nBan co the nhap van ban tai day. He thong se tong hop giong noi va xuat ra file WAV chat luong cao.";
const DEFAULT_API_BASE = process.env.NEXT_PUBLIC_VIENEU_API_BASE || "/api/vieneu";

type EventLine = JobEvent & { at: string };
type WorkMode = "tts" | "novel";

function nowLabel() {
  return new Date().toLocaleTimeString("en-GB", { hour12: false });
}

function statusTone(status?: JobStatus) {
  if (status === "completed") return "good";
  if (status === "failed") return "bad";
  if (status === "running") return "active";
  return "muted";
}

export default function Page() {
  const [serverUrl, setServerUrl] = useLocalStorageState("vieneu.serverUrl", DEFAULT_API_BASE);
  const [mode, setMode] = useLocalStorageState<WorkMode>("vieneu.mode", "tts");
  const [selectedModel, setSelectedModel] = useLocalStorageState("vieneu.selectedModel", "pnnbao-ump/VieNeu-TTS-v2-Turbo");
  const [chapterTitle, setChapterTitle] = useLocalStorageState("vieneu.chapterTitle", "Chapter 1");
  const [text, setText] = useLocalStorageState("vieneu.text", DEFAULT_TEXT);
  const [voiceReferenceId, setVoiceReferenceId] = useLocalStorageState("vieneu.voiceReferenceId", "");
  const [voiceReferencePath, setVoiceReferencePath] = useLocalStorageState("vieneu.voiceReferencePath", "");
  const [recentJobs, setRecentJobs] = useLocalStorageState<JobRecord[]>("vieneu.recentJobs", []);
  const [recentChapterJobs, setRecentChapterJobs] = useLocalStorageState<ChapterJobRecord[]>("vieneu.recentChapterJobs", []);
  const [healthOk, setHealthOk] = useState(false);
  const [runtime, setRuntime] = useState<RuntimeInfo | null>(null);
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [voices, setVoices] = useState<VoiceInfo[]>([]);
  const [voicesLoading, setVoicesLoading] = useState(false);
  const [activeJob, setActiveJob] = useState<JobRecord | null>(null);
  const [activeChapterJob, setActiveChapterJob] = useState<ChapterJobRecord | null>(null);
  const [events, setEvents] = useState<EventLine[]>([]);
  const [isSubmitting, setSubmitting] = useState(false);
  const [activeTab, setActiveTab] = useState<"jobs" | "events" | "audio">("jobs");
  const [lastError, setLastError] = useState<string | null>(null);
  const socketRef = useRef<WebSocket | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const refreshServer = useCallback(async () => {
    setLastError(null);
    try {
      const [health, runtimeInfo, modelList] = await Promise.all([
        fetchHealth(serverUrl),
        fetchRuntime(serverUrl),
        fetchModels(serverUrl)
      ]);
      setHealthOk(health.ok);
      setRuntime(runtimeInfo);
      setModels(modelList);
      const defaultModel = modelList.find((item) => item.default)?.id || modelList[0]?.id;
      if (defaultModel && !modelList.some((item) => item.id === selectedModel)) {
        setSelectedModel(defaultModel);
      }
    } catch (error) {
      setHealthOk(false);
      setRuntime(null);
      setModels([]);
      setLastError(error instanceof Error ? error.message : "Unable to reach VieNeu server");
    }
  }, [selectedModel, serverUrl, setSelectedModel]);

  useEffect(() => {
    refreshServer();
  }, [refreshServer]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const hostname = window.location.hostname;
    const isLocalPage = hostname === "localhost" || hostname === "127.0.0.1";
    const isLocalBackend = /^https?:\/\/(localhost|127\.0\.0\.1):8000\/?$/.test(serverUrl);
    if (!isLocalPage && isLocalBackend) {
      setServerUrl(DEFAULT_API_BASE);
    }
  }, [serverUrl, setServerUrl]);

  useEffect(() => {
    if (!healthOk || !selectedModel) {
      setVoices([]);
      return;
    }
    let cancelled = false;
    setVoicesLoading(true);
    fetchModelVoices(serverUrl, selectedModel)
      .then((voiceList) => {
        if (cancelled) return;
        setVoices(voiceList);
        const defaultVoice = voiceList.find((voice) => voice.default)?.id || voiceList[0]?.id || "";
        if (defaultVoice && !voiceList.some((voice) => voice.id === voiceReferenceId)) {
          setVoiceReferenceId(defaultVoice);
        }
        if (!voiceList.length) {
          setVoiceReferenceId("");
        }
      })
      .catch((error) => {
        if (cancelled) return;
        setVoices([]);
        setVoiceReferenceId("");
        setLastError(error instanceof Error ? error.message : "Unable to load model voices");
      })
      .finally(() => {
        if (!cancelled) setVoicesLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [healthOk, selectedModel, serverUrl, setVoiceReferenceId, voiceReferenceId]);

  useEffect(() => {
    return () => {
      socketRef.current?.close();
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  const subscribeToJob = useCallback((jobId: string) => {
    socketRef.current?.close();
    if (pollRef.current) clearInterval(pollRef.current);
    const socket = openJobSocket(serverUrl, jobId);
    socketRef.current = socket;

    const applyJob = (job: JobRecord) => {
      setActiveJob((current) => (current?.job_id === job.job_id ? job : current));
      setRecentJobs((jobs) => jobs.map((item) => (item.job_id === job.job_id ? job : item)));
    };

    const poll = async () => {
      try {
        const job = await fetchJob(serverUrl, jobId);
        applyJob(job);
        if (job.status === "completed" || job.status === "failed") {
          if (pollRef.current) clearInterval(pollRef.current);
          pollRef.current = null;
        }
      } catch (error) {
        const event: EventLine = {
          type: "job.status",
          job_id: jobId,
          status: "running",
          progress: 0,
          error: error instanceof Error ? error.message : "Status polling failed",
          at: nowLabel()
        };
        setEvents((items) => [
          event,
          ...items
        ].slice(0, 60));
      }
    };

    pollRef.current = setInterval(poll, 1500);

    socket.onmessage = (message) => {
      const event = JSON.parse(message.data) as JobEvent;
      setEvents((items) => [{ ...event, at: nowLabel() }, ...items].slice(0, 60));
      setActiveJob((current) =>
        current && current.job_id === event.job_id
          ? {
              ...current,
              status: event.status,
              progress: event.progress,
              audio_url: event.audio_url !== undefined ? event.audio_url : current.audio_url,
              error: event.error ?? current.error
            }
          : current
      );
      setRecentJobs((jobs) =>
        jobs.map((job) =>
          job.job_id === event.job_id
            ? {
                ...job,
                status: event.status,
                progress: event.progress,
                audio_url: event.audio_url !== undefined ? event.audio_url : job.audio_url,
                error: event.error ?? job.error
              }
            : job
        )
      );
      if (event.status === "completed" || event.status === "failed") {
        poll();
      }
    };

    socket.onerror = () => {
      setEvents((items) => [
        { type: "job.failed", job_id: jobId, status: "failed", progress: 0, error: "WebSocket connection failed", at: nowLabel() },
        ...items
      ]);
    };

    socket.onclose = () => {
      poll();
    };
  }, [serverUrl, setRecentJobs]);

  const subscribeToChapterJob = useCallback((jobId: string) => {
    socketRef.current?.close();
    if (pollRef.current) clearInterval(pollRef.current);
    const socket = openChapterJobSocket(serverUrl, jobId);
    socketRef.current = socket;

    const applyJob = (job: ChapterJobRecord) => {
      setActiveChapterJob((current) => (current?.job_id === job.job_id ? job : current));
      setRecentChapterJobs((jobs) => jobs.map((item) => (item.job_id === job.job_id ? job : item)));
    };

    const poll = async () => {
      try {
        const job = await fetchChapterJob(serverUrl, jobId);
        applyJob(job);
        if (job.status === "completed" || job.status === "failed") {
          if (pollRef.current) clearInterval(pollRef.current);
          pollRef.current = null;
        }
      } catch (error) {
        const event: EventLine = {
          type: "chapter.status",
          job_id: jobId,
          status: "running",
          progress: 0,
          error: error instanceof Error ? error.message : "Chapter status polling failed",
          at: nowLabel()
        };
        setEvents((items) => [event, ...items].slice(0, 60));
      }
    };

    pollRef.current = setInterval(poll, 1500);

    socket.onmessage = (message) => {
      const event = JSON.parse(message.data) as JobEvent;
      setEvents((items) => [{ ...event, at: nowLabel() }, ...items].slice(0, 60));
      setActiveChapterJob((current) =>
        current && current.job_id === event.job_id
          ? {
              ...current,
              status: event.status,
              progress: event.progress,
              audio_url: event.audio_url !== undefined ? event.audio_url : current.audio_url,
              error: event.error ?? current.error
            }
          : current
      );
      setRecentChapterJobs((jobs) =>
        jobs.map((job) =>
          job.job_id === event.job_id
            ? {
                ...job,
                status: event.status,
                progress: event.progress,
                audio_url: event.audio_url !== undefined ? event.audio_url : job.audio_url,
                error: event.error ?? job.error
              }
            : job
        )
      );
      if (event.status === "completed" || event.status === "failed") {
        poll();
      }
    };

    socket.onerror = () => {
      setEvents((items) => [
        { type: "chapter.failed", job_id: jobId, status: "failed", progress: 0, error: "Chapter WebSocket connection failed", at: nowLabel() },
        ...items
      ]);
    };

    socket.onclose = () => {
      poll();
    };
  }, [serverUrl, setRecentChapterJobs]);

  const handleGenerate = async () => {
    if (!text.trim()) {
      setLastError("Text is required.");
      return;
    }
    setSubmitting(true);
    setLastError(null);
    try {
      if (mode === "novel") {
        const created = await createChapterJob(serverUrl, {
          title: chapterTitle.trim() || "Novel chapter",
          text,
          model_id: selectedModel,
          voice_reference_id: voiceReferenceId.trim() || null,
          voice_reference_path: voiceReferencePath.trim() || null,
          format: "wav"
        });
        const job: ChapterJobRecord = {
          job_id: created.job_id,
          title: chapterTitle.trim() || "Novel chapter",
          status: created.status,
          progress: 0,
          audio_url: null,
          error: null,
          segment_count: 0,
          completed_segments: 0,
          failed_segments: 0,
          paragraph_count: 0,
          manifest_path: null,
          segments: []
        };
        setActiveChapterJob(job);
        setRecentChapterJobs((jobs) => [job, ...jobs.filter((item) => item.job_id !== job.job_id)].slice(0, 8));
        setEvents((items) => [{ type: "chapter.status", job_id: job.job_id, status: "queued", progress: 0, message: "Chapter job created", at: nowLabel() }, ...items]);
        setActiveTab("jobs");
        subscribeToChapterJob(job.job_id);
        return;
      }
      const created = await createJob(serverUrl, {
        text,
        model_id: selectedModel,
        voice_reference_id: voiceReferenceId.trim() || null,
        voice_reference_path: voiceReferencePath.trim() || null,
        format: "wav"
      });
      const job: JobRecord = {
        job_id: created.job_id,
        status: created.status,
        progress: 0,
        audio_url: null,
        error: null
      };
      setActiveJob(job);
      setRecentJobs((jobs) => [job, ...jobs.filter((item) => item.job_id !== job.job_id)].slice(0, 8));
      setEvents((items) => [{ type: "job.status", job_id: job.job_id, status: "queued", progress: 0, message: "Job created", at: nowLabel() }, ...items]);
      setActiveTab("jobs");
      subscribeToJob(job.job_id);
    } catch (error) {
      setLastError(error instanceof Error ? error.message : "Failed to create job");
    } finally {
      setSubmitting(false);
    }
  };

  const currentJobs = mode === "novel" ? recentChapterJobs : recentJobs;
  const currentActiveJob = mode === "novel" ? activeChapterJob : activeJob;

  const counts = useMemo(() => {
    return currentJobs.reduce(
      (acc, job) => {
        acc[job.status] += 1;
        return acc;
      },
      { queued: 0, running: 0, completed: 0, failed: 0 } as Record<JobStatus, number>
    );
  }, [currentJobs]);

  const activeAudio = currentActiveJob?.status === "completed" && currentActiveJob.audio_url
    ? mode === "novel" ? chapterAudioUrl(serverUrl, currentActiveJob.job_id) : jobAudioUrl(serverUrl, currentActiveJob.job_id)
    : "";
  const maxTextLength = mode === "novel" ? 120000 : 3000;

  return (
    <main className="app-shell">
      <ServiceWorkerRegister />
      <header className="topbar">
        <div className="brand">
          <span className="brand-mark"><Waves size={24} /></span>
          <span>VieNeu Studio</span>
        </div>
        <label className="server-control">
          <span>Server</span>
          <span className={`status-dot ${healthOk ? "online" : "offline"}`} />
          <input value={serverUrl} onChange={(event) => setServerUrl(event.target.value)} aria-label="Server URL" />
        </label>
        <button className="icon-button" type="button" onClick={refreshServer} aria-label="Refresh server">
          <RefreshCw size={20} />
        </button>
        <div className="runtime-pill">
          <span>Runtime</span>
          <strong>{runtime ? `${runtime.device.toUpperCase()} (${runtime.dtype})` : "Offline"}</strong>
        </div>
        <label className="model-control">
          <span>Model</span>
          <select value={selectedModel} onChange={(event) => setSelectedModel(event.target.value)}>
            {(models.length ? models : [{ id: selectedModel, default: true }]).map((model) => (
              <option key={model.id} value={model.id}>{model.id}</option>
            ))}
          </select>
        </label>
      </header>

      <section className="workspace">
        <div className="editor-pane">
          <div className="section-head">
            <h1>{mode === "novel" ? "Novel Chapter" : "Text"}</h1>
            <div className="head-actions">
              <button type="button" onClick={() => setText("")}>Clear</button>
              <span>{text.length} / {maxTextLength}</span>
            </div>
          </div>
          <div className="mode-switch" aria-label="Synthesis mode">
            <button type="button" className={mode === "tts" ? "active" : ""} onClick={() => setMode("tts")}>
              <Sparkles size={16} /> TTS
            </button>
            <button type="button" className={mode === "novel" ? "active" : ""} onClick={() => setMode("novel")}>
              <BookOpen size={16} /> Novel
            </button>
          </div>
          {mode === "novel" ? (
            <label className="field">
              <span>Chapter title</span>
              <input value={chapterTitle} onChange={(event) => setChapterTitle(event.target.value)} placeholder="Chapter 1" />
            </label>
          ) : null}
          <textarea
            value={text}
            onChange={(event) => setText(event.target.value)}
            maxLength={maxTextLength}
            spellCheck={false}
            aria-label={mode === "novel" ? "Novel chapter text" : "Text to synthesize"}
          />

          <div className="voice-grid">
            <div>
              <h2>Voice</h2>
              <label className="field">
                <span>Preset voice from model {voicesLoading ? "(loading...)" : voices.length ? `(${voices.length})` : "(none found)"}</span>
                <select value={voiceReferenceId} onChange={(event) => setVoiceReferenceId(event.target.value)} disabled={voicesLoading || !voices.length}>
                  {!voices.length ? <option value="">No preset voices</option> : null}
                  {voices.map((voice) => (
                    <option key={voice.id} value={voice.id}>
                      {voice.description || voice.id}
                    </option>
                  ))}
                </select>
              </label>
            </div>
            <label className="drop-target">
              <Upload size={24} />
              <span>Reference path</span>
              <input value={voiceReferencePath} onChange={(event) => setVoiceReferencePath(event.target.value)} placeholder="D:\\voices\\sample.wav" />
            </label>
          </div>

          <div className="output-grid">
            <label><span>Format</span><input value="WAV" readOnly /></label>
            <label><span>Sample Rate</span><input value="24000" readOnly /></label>
            <label><span>Channels</span><input value="1 (Mono)" readOnly /></label>
            <label><span>Backend</span><input value={runtime?.backend || "torch"} readOnly /></label>
          </div>

          {lastError ? <div className="error-line"><CircleAlert size={16} />{lastError}</div> : null}
          <button className="generate-button" type="button" onClick={handleGenerate} disabled={isSubmitting || !healthOk}>
            {isSubmitting ? <Loader2 className="spin" size={20} /> : <Sparkles size={20} />}
            {mode === "novel" ? "Generate Chapter WAV" : "Generate WAV"}
          </button>
        </div>

        <aside className="job-pane">
          <nav className="tabs" aria-label="Job panels">
            {(["jobs", "events", "audio"] as const).map((tab) => (
              <button key={tab} className={activeTab === tab ? "active" : ""} type="button" onClick={() => setActiveTab(tab)}>
                {tab[0].toUpperCase() + tab.slice(1)}
              </button>
            ))}
          </nav>

          {activeTab === "jobs" ? (
            <div className="panel-flow">
              <div className="status-cards">
                {(["queued", "running", "completed", "failed"] as JobStatus[]).map((status) => (
                  <div key={status} className={`status-card ${statusTone(status)}`}>
                    <span>{status}</span>
                    <strong>{counts[status]}</strong>
                  </div>
                ))}
              </div>
              <div className="job-list">
                {currentJobs.length ? currentJobs.map((job, index) => (
                  <button
                    key={job.job_id}
                    className={`job-row ${currentActiveJob?.job_id === job.job_id ? "selected" : ""}`}
                    type="button"
                    onClick={() => mode === "novel" ? setActiveChapterJob(job as ChapterJobRecord) : setActiveJob(job)}
                  >
                    <span className={`row-icon ${statusTone(job.status)}`}>{job.status === "running" ? <Play size={16} /> : job.status === "completed" ? <CheckCircle2 size={16} /> : job.status === "failed" ? <CircleAlert size={16} /> : <Pause size={16} />}</span>
                    <strong>#{currentJobs.length - index}</strong>
                  <span>{job.status}</span>
                  {isChapterJob(job) ? <small>{job.paragraph_count}p / {job.segment_count}c</small> : null}
                  <progress value={job.progress} max={1} />
                  <small>{Math.round(job.progress * 100)}%</small>
                </button>
                )) : <EmptyState title="No jobs yet" text="Create a TTS job to see progress here." />}
              </div>
            </div>
          ) : null}

          {activeTab === "events" ? (
            <div className="event-log">
              {events.length ? events.map((event, index) => (
                <div key={`${event.job_id}-${event.at}-${index}`} className="event-line">
                  <time>{event.at}</time>
                  <strong>{event.type}</strong>
                  <span>{event.message || event.error || `${event.status} ${Math.round(event.progress * 100)}%`}</span>
                </div>
              )) : <EmptyState title="No events" text="WebSocket events appear after job creation." />}
            </div>
          ) : null}

          {activeTab === "audio" ? (
            <div className="audio-panel">
              <div className="audio-head">
                <h2>Audio {currentActiveJob ? `(${currentActiveJob.job_id.slice(0, 8)})` : ""}</h2>
                <span>{currentActiveJob?.status || "No job"}</span>
              </div>
              {mode === "novel" && activeChapterJob ? (
                <div className="chapter-meter">
                  <strong>{activeChapterJob.title}</strong>
                  <span>
                    {activeChapterJob.completed_segments} / {activeChapterJob.segment_count || "?"} chunks
                    {activeChapterJob.paragraph_count ? ` across ${activeChapterJob.paragraph_count} paragraphs` : ""}
                  </span>
                  <progress value={activeChapterJob.completed_segments} max={Math.max(activeChapterJob.segment_count, 1)} />
                  {activeChapterJob.segments.length ? (
                    <small>
                      Current: {chapterProgressLabel(activeChapterJob)}
                    </small>
                  ) : null}
                </div>
              ) : null}
              <div className="waveform" aria-hidden="true">
                {Array.from({ length: 52 }).map((_, index) => <span key={index} style={{ height: `${20 + ((index * 13) % 44)}%` }} />)}
              </div>
              {activeAudio ? <audio controls src={activeAudio} onError={() => setLastError("Audio download failed. The backend connection was reset or the file is no longer available.")} /> : <div className="audio-placeholder"><Volume2 size={18} />Audio appears when a job completes.</div>}
              <a className={`download-link ${activeAudio ? "" : "disabled"}`} href={activeAudio || "#"} download>
                <Download size={18} /> Download WAV
              </a>
            </div>
          ) : null}
        </aside>
      </section>

      <footer className="diagnostics">
        <Diagnostic label="CUDA" value={runtime?.device === "cuda" ? "Enabled" : "CPU"} good={!!runtime} />
        <Diagnostic label="GPU" value={runtime?.gpu_name || (runtime ? "not selected" : "none")} good={runtime?.device === "cuda"} />
        <Diagnostic label="Compute" value={runtime?.compute_capability?.join(".") || (runtime ? "not selected" : "none")} good={runtime?.device === "cuda"} />
        <Diagnostic label="Backend" value={runtime?.backend || "torch"} good={!!runtime} />
        <Diagnostic label="DType" value={runtime?.dtype || "float32"} good={!!runtime} />
        <Diagnostic label="LMDeploy" value={runtime?.lmdeploy_enabled ? "Enabled" : "Disabled"} good={!runtime?.lmdeploy_enabled} />
        <div className="diagnostic diagnostic-reason">
          <span>Runtime Reason</span>
          <strong>{runtime?.reason || lastError || "Waiting for backend runtime"}</strong>
        </div>
      </footer>
    </main>
  );
}

function EmptyState({ title, text }: { title: string; text: string }) {
  return (
    <div className="empty-state">
      <Activity size={22} />
      <strong>{title}</strong>
      <span>{text}</span>
    </div>
  );
}

function Diagnostic({ label, value, good }: { label: string; value: string; good: boolean }) {
  return (
    <div className="diagnostic">
      <span>{label}</span>
      <strong>{value}</strong>
      <CheckCircle2 className={good ? "ok" : "dim"} size={16} />
    </div>
  );
}

function chapterProgressLabel(job: ChapterJobRecord) {
  const current = job.segments.find((segment) => segment.status === "running")
    || job.segments.find((segment) => segment.status === "queued")
    || job.segments.at(-1);
  if (!current) return "Preparing chapter";
  return `paragraph ${current.paragraph_index}, chunk ${current.paragraph_segment_index}/${current.paragraph_segment_count}`;
}

function isChapterJob(job: JobRecord | ChapterJobRecord): job is ChapterJobRecord {
  return "paragraph_count" in job && "segment_count" in job;
}
