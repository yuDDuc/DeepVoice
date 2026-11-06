"use client";
import React, { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  Activity,
  ArrowDownToLine,
  ArrowLeftRight,
  ArrowRight,
  AudioLines,
  Check,
  ChevronDown,
  ChevronRight,
  CircleHelp,
  Clock3,
  Cloud,
  Cpu,
  Database,
  FileAudio,
  Globe2,
  History,
  Layers3,
  Loader2,
  LogOut,
  Mic,
  Monitor,
  Play,
  Plus,
  Settings2,
  ShieldCheck,
  Sparkles,
  Square,
  Trash2,
  Upload,
  Wallet,
  X,
  Zap,
  Menu,
  Sun,
  Moon,
} from "lucide-react";
import { api, download, Model, Segment, User, WS } from "@/lib/api";
import { mp3ToWav } from "@/lib/audio";
import { Button } from "@/components/ui/button";
const nav = [
  { path: "/app/translate/live", label: "Không gian dịch", icon: AudioLines },
  {
    path: "/app/translate/upload",
    label: "Dịch tệp âm thanh",
    icon: FileAudio,
  },
  { path: "/app/history", label: "Lịch sử hội thoại", icon: History },
  { path: "/app/models", label: "Model & nguồn chạy", icon: Layers3 },
  { path: "/app/monitor", label: "Giám sát tài nguyên", icon: Activity },
  { path: "/app/billing", label: "Ví & thanh toán", icon: Wallet },
];
function Brand() {
  return (
    <Link className="brand" href="/">
      <span className="brand-icon">
        <AudioLines size={23} />
      </span>
      <span>
        avrt<span className="brand-light">studio</span>
        <small>ADAPTIVE VOICE TRANSLATION</small>
      </span>
    </Link>
  );
}
function Pill({
  children,
  tone = "neutral",
}: {
  children: React.ReactNode;
  tone?: string;
}) {
  return <span className={`pill ${tone}`}>{children}</span>;
}
function Empty({
  icon: Icon = AudioLines,
  title,
  text,
}: {
  icon?: React.ElementType;
  title: string;
  text: string;
}) {
  return (
    <div className="empty">
      <div className="empty-symbol">
        <Icon size={30} />
      </div>
      <h3>{title}</h3>
      <p>{text}</p>
    </div>
  );
}
function Metric({
  label,
  value,
  unit,
  percent,
}: {
  label: string;
  value: string;
  unit?: string;
  percent?: number;
}) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong>
        {value}
        <small>{unit}</small>
      </strong>
      {percent !== undefined && (
        <div className="meter">
          <i style={{ width: `${Math.min(100, Math.max(0, percent))}%` }} />
        </div>
      )}
    </div>
  );
}
export default function Studio() {
  const path = usePathname();
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [checking, setChecking] = useState(true);
  const [error, setError] = useState("");
  const [mobile, setMobile] = useState(false);
  const [dark, setDark] = useState(false);
  const loadUser = useCallback(async () => {
    try {
      setUser(await api("/auth/me"));
    } catch {
      try {
        setUser(await api("/auth/refresh", { method: "POST" }));
      } catch {
        setUser(null);
      }
    } finally {
      setChecking(false);
    }
  }, []);
  useEffect(() => {
    void loadUser();
  }, [loadUser]);
  useEffect(() => {
    if (!checking && !user && path.startsWith("/app"))
      router.replace("/auth/login");
    if (!checking && !user && path.startsWith("/admin"))
      router.replace("/auth/login");
  }, [checking, user, path, router]);
  useEffect(() => {
    document.documentElement.dataset.theme = dark ? "dark" : "light";
  }, [dark]);
  useEffect(() => {
    setError("");
    setMobile(false);
  }, [path]);
  if (path === "/") return <Landing user={user} />;
  if (path.startsWith("/auth")) return <Auth path={path} onUser={setUser} />;
  if (checking || !user)
    return (
      <div className="splash">
        <Loader2 className="spin" /> Đang mở không gian làm việc…
      </div>
    );
  const active = nav.find((n) => path.startsWith(n.path));
  const report = (e: unknown) =>
    setError(e instanceof Error ? e.message : String(e));
  return (
    <div className="shell">
      <aside className={`sidebar ${mobile ? "open" : ""}`}>
        <Brand />
        <div className="workspace-switch">
          <div className="avatar teal">P</div>
          <span>
            Personal workspace<small>Không gian của bạn</small>
          </span>
          <ChevronDown size={15} />
        </div>
        <div className="nav-caption">WORKSPACE</div>
        <nav>
          {nav.map((n) => (
            <Link
              key={n.path}
              href={n.path}
              className={path.startsWith(n.path) ? "active" : ""}
            >
              <n.icon size={19} />
              {n.label}
              {n.path === nav[0].path && <span className="nav-dot" />}
            </Link>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="offline-card">
            <ShieldCheck size={21} />
            <strong>Dữ liệu trong tầm kiểm soát</strong>
            <p>Chọn model local hoặc chỉ gửi lên cloud khi bạn đồng ý.</p>
            <Link href="/app/settings">
              Quản lý quyền riêng tư <ArrowRight size={14} />
            </Link>
          </div>
          <Link className="side-setting" href="/app/settings">
            <Settings2 size={18} /> Cài đặt tài khoản
          </Link>
          <button
            className="profile"
            onClick={() => {
              void api("/auth/logout", { method: "POST" })
                .then(() => {
                  setUser(null);
                  router.push("/auth/login");
                })
                .catch(report);
            }}
          >
            <div className="avatar">{user.email[0].toUpperCase()}</div>
            <span>
              {user.email.split("@")[0]}
              <small>
                {user.role === "admin" ? "Quản trị viên" : "Tài khoản cá nhân"}
              </small>
            </span>
            <LogOut size={17} />
          </button>
        </div>
      </aside>
      <div className="main">
        <header className="topbar">
          <div className="breadcrumb">
            <button
              className="icon-button mobile-toggle"
              aria-label="Mở menu"
              onClick={() => setMobile(!mobile)}
            >
              <Menu size={20} />
            </button>
            <span>Workspace</span>
            <ChevronRight size={14} />
            <strong>{active?.label || "Cài đặt"}</strong>
          </div>
          <div className="top-actions">
            <Pill tone="green">
              <span className="dot" /> Phiên bảo mật
            </Pill>
            <button
              className="icon-button"
              aria-label="Đổi giao diện"
              onClick={() => setDark(!dark)}
            >
              {dark ? <Sun size={18} /> : <Moon size={18} />}
            </button>
            <div className="avatar small">{user.email[0].toUpperCase()}</div>
          </div>
        </header>
        <main className="content">
          {error && (
            <div role="alert" className="alert error">
              {error}
              <button aria-label="Đóng lỗi" onClick={() => setError("")}>
                <X size={16} />
              </button>
            </div>
          )}
          {path.includes("/translate/live") ? (
            <Translator report={report} />
          ) : path.includes("/translate/upload") ? (
            <UploadPage report={report} />
          ) : path.includes("/history") ? (
            <HistoryPage report={report} />
          ) : path.includes("/models") ? (
            <ModelsPage user={user} report={report} />
          ) : path.includes("/monitor") ? (
            <MonitorPage report={report} />
          ) : path.includes("/billing") ? (
            <BillingPage report={report} reloadUser={loadUser} />
          ) : path.startsWith("/admin") ? (
            <AdminPage report={report} />
          ) : (
            <SettingsPage user={user} report={report} />
          )}
        </main>
        <footer className="footer">
          <span>
            AVRT Studio <span className="muted">/</span> Development build 0.1
          </span>
          <span>
            <span className="dot" /> Model minh bạch. Dữ liệu của bạn.
          </span>
        </footer>
      </div>
    </div>
  );
}
function Landing({ user }: { user: User | null }) {
  return (
    <div className="landing">
      <header>
        <Brand />
        <Link href={user ? "/app/translate/live" : "/auth/login"}>
          Đăng nhập <ArrowRight size={16} />
        </Link>
      </header>
      <div className="hero">
        <Pill tone="green">
          <Sparkles size={13} /> KHÔNG GIAN DỊCH ANH ⇄ VIỆT
        </Pill>
        <h1>
          Hiểu nhau hơn.
          <br />
          <em>Từng câu nói.</em>
        </h1>
        <p>
          Biến lời nói thành kết nối. Dịch hội thoại, sử dụng model của riêng
          bạn và quan sát hiệu năng trong cùng một không gian.
        </p>
        <Button asChild>
          <Link href={user ? "/app/translate/live" : "/auth/register"}>
            Mở không gian dịch <ArrowRight size={17} />
          </Link>
        </Button>
        <div className="hero-facts">
          <span>
            <ShieldCheck size={16} /> Quyền riêng tư chủ động
          </span>
          <span>
            <Cpu size={16} /> HF hoặc model local
          </span>
          <span>
            <Activity size={16} /> Hiệu năng đo thực tế
          </span>
        </div>
      </div>
      <div className="hero-preview">
        <div className="preview-heading">
          <AudioLines /> Hội thoại không rào cản{" "}
          <Pill tone="green">EN ⇄ VI</Pill>
        </div>
        <div className="quote">
          <small>ENGLISH</small>
          <p>Hello, let’s build something together.</p>
        </div>
        <div className="quote translated">
          <small>TIẾNG VIỆT · VÍ DỤ MINH HỌA</small>
          <p>Xin chào, cùng nhau tạo nên điều gì đó nhé.</p>
        </div>
        <div className="preview-bottom">
          <span>
            <span className="dot" /> Kết nối bằng ngôn ngữ của bạn
          </span>
          <Mic size={22} />
        </div>
      </div>
    </div>
  );
}
function Auth({ path, onUser }: { path: string; onUser: (u: User) => void }) {
  const register = path.includes("register");
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    if (!register) {
      try {
        setEmail(localStorage.getItem("avrt:last-email") || "");
      } catch {
        // Browser storage can be unavailable in private mode.
      }
    }
  }, [register]);
  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const u = await api<User>(register ? "/auth/register" : "/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });
      try {
        localStorage.setItem("avrt:last-email", email.trim().toLowerCase());
      } catch {
        // Login still works without browser storage.
      }
      onUser(u);
      router.push("/app/translate/live");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="auth-page">
      <div className="auth-story">
        <Brand />
        <div>
          <Pill>YOUR WORDS. NEW POSSIBILITIES.</Pill>
          <h1>
            Mọi cuộc hội thoại
            <br />
            đều là một
            <br />
            <em>khởi đầu mới.</em>
          </h1>
          <p>
            Không gian dành cho ngôn ngữ, model
            <br />
            và những kết nối ý nghĩa.
          </p>
        </div>
        <span>
          ENGLISH <ArrowLeftRight size={16} /> TIẾNG VIỆT
        </span>
      </div>
      <div className="auth-form-wrap">
        <form className="auth-form" onSubmit={submit}>
          <Pill tone="green">AVRT WORKSPACE</Pill>
          <h1>{register ? "Bắt đầu kết nối." : "Chào mừng trở lại."}</h1>
          <p>
            {register
              ? "Tạo tài khoản để mở không gian dịch của bạn."
              : "Đăng nhập để tiếp tục những cuộc hội thoại."}
          </p>
          <label>
            Email
            <input
              required
              name={register ? "email" : "username"}
              type="email"
              autoComplete={register ? "email" : "username"}
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
            />
          </label>
          <label>
            Mật khẩu
            <input
              required
              name="password"
              type="password"
              minLength={10}
              maxLength={128}
              autoComplete={register ? "new-password" : "current-password"}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Ít nhất 10 ký tự"
            />
          </label>
          {error && (
            <div className="alert error" role="alert">
              {error}
            </div>
          )}
          <Button disabled={busy} type="submit">
            {busy ? <Loader2 className="spin" size={17} /> : null}
            {register ? "Tạo tài khoản" : "Đăng nhập"}
            <ArrowRight size={16} />
          </Button>
          <p className="auth-link">
            {register ? "Đã có tài khoản?" : "Chưa có tài khoản?"}{" "}
            <Link href={register ? "/auth/login" : "/auth/register"}>
              {register ? "Đăng nhập" : "Tạo tài khoản"}
            </Link>
          </p>
          <small>
            <ShieldCheck size={15} /> Token được giữ bằng cookie HttpOnly.
          </small>
        </form>
      </div>
    </div>
  );
}
function PageHead({
  eyebrow,
  title,
  text,
  children,
}: {
  eyebrow: string;
  title: string;
  text: string;
  children?: React.ReactNode;
}) {
  return (
    <div className="page-heading">
      <div>
        <div className="eyebrow">{eyebrow}</div>
        <h1>{title}</h1>
        <p>{text}</p>
      </div>
      {children}
    </div>
  );
}
function useMetrics(report: (e: unknown) => void) {
  const [data, setData] = useState<any>(null);
  useEffect(() => {
    let live = true;
    const load = () =>
      api("/metrics")
        .then((x) => {
          if (live) setData(x);
        })
        .catch((e) => {
          if (live) report(e);
        });
    void load();
    const t = setInterval(load, 1500);
    return () => {
      live = false;
      clearInterval(t);
    };
  }, []);
  return data;
}
function ResourcePanel({
  report,
  wide = false,
}: {
  report: (e: unknown) => void;
  wide?: boolean;
}) {
  const data = useMetrics(report);
  const local = data?.worker || data?.gateway;
  const gpu = local?.gpu?.[0];
  return (
    <section className={`panel resource-panel ${wide ? "wide" : ""}`}>
      <div className="panel-title">
        <span>
          <Activity size={17} /> Tài nguyên trực tiếp
        </span>
        <Pill tone={local ? "green" : "neutral"}>
          {local ? "LIVE" : "ĐANG KẾT NỐI"}
        </Pill>
      </div>
      <p className="resource-sub">
        {data?.worker ? "Inference worker" : "Máy chủ ứng dụng"} · mẫu{" "}
        {local?.sample_window_ms || "—"} ms
      </p>
      <div className="resource-grid">
        <Metric
          label="CPU hệ thống"
          value={local ? local.cpu_percent.toFixed(1) : "—"}
          unit="%"
          percent={local?.cpu_percent || 0}
        />
        <Metric
          label="Bộ nhớ RAM"
          value={local ? (local.ram_used_mb / 1024).toFixed(1) : "—"}
          unit={local ? `/ ${(local.ram_total_mb / 1024).toFixed(1)} GB` : "GB"}
          percent={local ? (local.ram_used_mb / local.ram_total_mb) * 100 : 0}
        />
        <Metric
          label="GPU hệ thống"
          value={gpu ? gpu.util_percent.toFixed(0) : "N/A"}
          unit={gpu ? "%" : undefined}
          percent={gpu?.util_percent || 0}
        />
        <Metric
          label="Bộ nhớ GPU"
          value={gpu ? (gpu.vram_used_mb / 1024).toFixed(2) : "—"}
          unit={gpu ? `/ ${(gpu.vram_total_mb / 1024).toFixed(1)} GB` : "GB"}
        />
      </div>
      <div className="latency-line">
        <span>
          <Clock3 size={14} /> Độ trễ inference P95
        </span>
        <strong>
          {data?.latency?.p95_ms != null
            ? `${Math.round(data.latency.p95_ms)} ms`
            : "Chưa có mẫu"}
        </strong>
      </div>
      <div className="resource-note">
        <CircleHelp size={14} />
        <span>
          {gpu
            ? "GPU đo toàn thiết bị."
            : "GPU không khả dụng trên máy chủ hiện tại."}{" "}
          Không đo được GPU của HF Remote.
        </span>
      </div>
    </section>
  );
}
function Translator({ report }: { report: (e: unknown) => void }) {
  const [direction, setDirection] = useState<"en-vi" | "vi-en">("vi-en");
  const [text, setText] = useState("");
  const [segments, setSegments] = useState<Segment[]>([]);
  const [busy, setBusy] = useState(false);
  const [recording, setRecording] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [models, setModels] = useState<Model[]>([]);
  const [tts, setTts] = useState(false);
  const [status, setStatus] = useState("Sẵn sàng khi bạn bắt đầu");
  const [lastSaved, setLastSaved] = useState(false);
  const stream = useRef<MediaStream | null>(null);
  const context = useRef<AudioContext | null>(null);
  const socket = useRef<WebSocket | null>(null);
  const source = useRef<MediaStreamAudioSourceNode | null>(null);
  const started = useRef(0);
  const pcmNode = useRef<AudioWorkletNode | null>(null);
  const queuedAudio = useRef<Array<{ mime: string; base64: string }>>([]);
  const directionTouched = useRef(false);
  useEffect(() => {
    void api<{ models: Model[] }>("/models")
      .then((x) => {
        setModels(x.models);
        if (directionTouched.current) return;
        const hasRealPair = (selected: "en-vi" | "vi-en") => {
          const roles =
            selected === "vi-en"
              ? ["ASR_VI", "MT_VI_EN"]
              : ["ASR_EN", "MT_EN_VI"];
          return roles.every((role) => {
            const model = x.models.find((item) => item.role === role);
            return model && model.source !== "mock" && model.preflight.ok;
          });
        };
        if (hasRealPair("vi-en")) setDirection("vi-en");
        else if (hasRealPair("en-vi")) setDirection("en-vi");
      })
      .catch(report);
    return () => cleanup();
  }, []);
  function cleanup() {
    queuedAudio.current = [];
    stream.current?.getTracks().forEach((t) => t.stop());
    stream.current = null;
    source.current?.disconnect();
    source.current = null;
    if (context.current) void context.current.close().catch(() => {});
    context.current = null;
    socket.current?.close();
    socket.current = null;
  }
  async function playQueued() {
    const audio = queuedAudio.current.splice(0);
    for (const clip of audio) {
      await new Promise<void>((resolve) => {
        const a = new Audio(`data:${clip.mime};base64,${clip.base64}`);
        a.onended = () => resolve();
        a.onerror = () => resolve();
        void a.play().catch(() => resolve());
      });
    }
  }
  function add(result: Segment) {
    setSegments((items) => [...items, result]);
    setLastSaved(result.saved);
    if (result.audio) {
      queuedAudio.current.push(result.audio);
      if (!stream.current) void playQueued();
    }
  }
  async function translate() {
    if (!text.trim()) return;
    setBusy(true);
    try {
      const result = await api<Segment>("/translate/text", {
        method: "POST",
        body: JSON.stringify({ text, direction, tts }),
      });
      add(result);
      setText("");
    } catch (e) {
      report(e);
    } finally {
      setBusy(false);
    }
  }
  async function startMic() {
    if (recording) {
      source.current?.disconnect();
      stream.current?.getTracks().forEach((t) => t.stop());
      stream.current = null;
      pcmNode.current?.port.postMessage("flush");
      setRecording(false);
      setProcessing(true);
      setStatus("Đang hoàn tất đoạn cuối…");
      return;
    }
    try {
      if (!navigator.mediaDevices?.getUserMedia)
        throw new Error("Microphone cần HTTPS hoặc localhost.");
      const mic = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
        video: false,
      });
      stream.current = mic;
      const { ticket } = await api<{ ticket: string }>("/ws-ticket", {
        method: "POST",
      });
      const ws = new WebSocket(
        new URL(WS, window.location.href.replace(/^http/, "ws")),
      );
      socket.current = ws;
      let seq = 0;
      let ack = -1;
      let ready = false;
      started.current = Date.now();
      ws.onopen = () => ws.send(JSON.stringify({ ticket, direction, tts }));
      ws.onmessage = async (event) => {
        try {
          const msg = JSON.parse(event.data);
          if (msg.type === "ready" && !ready) {
            ready = true;
            const ctx = new AudioContext({ sampleRate: msg.sample_rate });
            context.current = ctx;
            if (ctx.sampleRate !== msg.sample_rate)
              throw new Error(
                "Trình duyệt không hỗ trợ sample rate đã cấu hình.",
              );
            await ctx.audioWorklet.addModule("/pcm-worklet.js");
            const node = new AudioWorkletNode(ctx, "avrt-pcm", {
              processorOptions: {
                frameSamples: Math.round(
                  (msg.sample_rate * msg.frame_ms) / 1000,
                ),
              },
            });
            pcmNode.current = node;
            source.current = ctx.createMediaStreamSource(mic);
            source.current.connect(node);
            const silent = ctx.createGain();
            silent.gain.value = 0;
            node.connect(silent);
            silent.connect(ctx.destination);
            node.port.onmessage = (event) => {
              if (event.data === "flushed") {
                ws.send(JSON.stringify({ type: "stop" }));
                return;
              }
              if (ws.readyState !== WebSocket.OPEN) return;
              if (seq - ack > 32 || ws.bufferedAmount > 1024 * 1024) {
                report(
                  new Error(
                    "Inference chậm hơn audio; đã dừng để tránh mất tiếng. Thử model nhỏ hơn hoặc tải WAV ngắn.",
                  ),
                );
                cleanup();
                setRecording(false);
                setProcessing(false);
                return;
              }
              const pcm = event.data as ArrayBuffer;
              const frame = new ArrayBuffer(12 + pcm.byteLength);
              const view = new DataView(frame);
              view.setUint32(0, seq++, true);
              view.setFloat64(4, Date.now() - started.current, true);
              new Uint8Array(frame, 12).set(new Uint8Array(pcm));
              ws.send(frame);
            };
            setRecording(true);
            setStatus(
              msg.mock
                ? "Đang nghe · ASR mock minh họa"
                : "Đang nghe · xử lý theo khoảng lặng",
            );
          } else if (msg.type === "ack") {
            ack = msg.seq;
          } else if (msg.type === "processing") {
            setProcessing(true);
            setStatus("Đang nhận dạng và dịch…");
          } else if (msg.type === "segment") {
            add(msg);
            setProcessing(false);
            setStatus("Đã nhận bản dịch · tiếp tục nghe");
          } else if (msg.type === "done") {
            setProcessing(false);
            setStatus("Đã kết thúc hội thoại");
          } else if (msg.type === "error") {
            report(new Error(msg.message));
            cleanup();
            setRecording(false);
            setProcessing(false);
          }
        } catch (e) {
          report(e);
          cleanup();
          setRecording(false);
          setProcessing(false);
        }
      };
      ws.onerror = () => {
        report(
          new Error(
            "Không kết nối được WebSocket. Kiểm tra backend và NEXT_PUBLIC_WS_URL.",
          ),
        );
        cleanup();
        setRecording(false);
        setProcessing(false);
      };
      ws.onclose = () => {
        setRecording(false);
        setProcessing(false);
        stream.current?.getTracks().forEach((t) => t.stop());
        if (context.current) void context.current.close().catch(() => {});
        context.current = null;
        void playQueued();
      };
    } catch (e) {
      report(e);
      cleanup();
      setRecording(false);
      setProcessing(false);
    }
  }
  const mt = models.find(
    (m) => m.role === (direction === "en-vi" ? "MT_EN_VI" : "MT_VI_EN"),
  );
  const asr = models.find(
    (m) => m.role === (direction === "en-vi" ? "ASR_EN" : "ASR_VI"),
  );
  return (
    <>
      <PageHead
        eyebrow="TRANSLATION STUDIO"
        title="Mỗi câu nói, một kết nối."
        text="Dịch Anh ⇄ Việt, kiểm tra bản dịch và theo dõi hiệu năng ngay khi nói."
      >
        <Button
          variant="outline"
          disabled={recording || processing}
          onClick={() => {
            setSegments([]);
            setStatus("Sẵn sàng khi bạn bắt đầu");
          }}
        >
          <Plus size={16} /> Hội thoại mới
        </Button>
      </PageHead>
      <div className="studio-grid">
        <div className="studio-main">
          <section className="panel translator-panel">
            <div className="translator-toolbar">
              <div className="language-switch">
                <span>
                  <span className="lang-badge">
                    {direction === "en-vi" ? "EN" : "VI"}
                  </span>
                  {direction === "en-vi" ? "Tiếng Anh" : "Tiếng Việt"}
                </span>
                <button
                  aria-label="Đảo chiều dịch"
                  disabled={recording || processing || busy}
                  onClick={() => {
                    directionTouched.current = true;
                    setDirection(direction === "en-vi" ? "vi-en" : "en-vi");
                  }}
                >
                  <ArrowLeftRight size={17} />
                </button>
                <span>
                  <span className="lang-badge">
                    {direction === "en-vi" ? "VI" : "EN"}
                  </span>
                  {direction === "en-vi" ? "Tiếng Việt" : "Tiếng Anh"}
                </span>
              </div>
              <Pill tone="green">
                <ShieldCheck size={12} /> Kiểm tra số & phủ định
              </Pill>
            </div>
            <div className="model-strip">
              <Cpu size={14} />
              <span>
                {asr && mt
                  ? `Nhận dạng: ${asr.source === "mock" ? "MOCK" : "AI thật"} · Dịch: ${mt.source === "mock" ? "MOCK" : "AI thật"}`
                  : "Đang đọc cấu hình model"}
              </span>
              <Link href="/app/models">
                Cấu hình <ChevronRight size={13} />
              </Link>
            </div>
            <div className="transcript-heading">
              <span>HỘI THOẠI</span>
              <span>{segments.length.toString().padStart(2, "0")} ĐOẠN</span>
            </div>
            <div className="transcript" aria-live="polite">
              {segments.length === 0 ? (
                <Empty
                  title="Một cuộc trò chuyện mới"
                  text="Nhấn micro để bắt đầu nói, hoặc nhập nội dung bên dưới. Bản gốc và bản dịch sẽ xuất hiện ở đây."
                />
              ) : (
                segments.map((s, i) => (
                  <article className="segment" key={s.id}>
                    <div className="segment-index">
                      {(i + 1).toString().padStart(2, "0")}
                    </div>
                    <div className="segment-body">
                      <div className="segment-meta">
                        <span>
                          {s.direction === "en-vi" ? "ENGLISH" : "TIẾNG VIỆT"}
                        </span>
                        <Pill
                          tone={
                            s.mock
                              ? "amber"
                              : s.state === "confirmed"
                                ? "green"
                                : "amber"
                          }
                        >
                          {s.mock
                            ? "MOCK"
                            : s.state === "confirmed"
                              ? "Đã ổn định"
                              : "Cần kiểm tra"}
                        </Pill>
                        <small>{Math.round(s.timings.total_ms)} ms</small>
                      </div>
                      <p className="source-text">{s.source_text}</p>
                      <div className="target-text">
                        <span className="translation-marker" />
                        {s.target_text}
                      </div>
                      {s.verification.warnings.map((w) => (
                        <div className="warning-text" key={w}>
                          {w}
                        </div>
                      ))}
                    </div>
                  </article>
                ))
              )}
            </div>
            <div className="compose">
              <textarea
                aria-label="Nội dung cần dịch"
                placeholder={
                  direction === "en-vi"
                    ? "Nhập tiếng Anh để thử bản dịch…"
                    : "Nhập tiếng Việt để thử bản dịch…"
                }
                value={text}
                onChange={(e) => setText(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
                    e.preventDefault();
                    void translate();
                  }
                }}
              />
              <div>
                <span>Ctrl + Enter để dịch</span>
                <Button
                  size="sm"
                  variant="outline"
                  disabled={busy || recording || !text.trim()}
                  onClick={() => void translate()}
                >
                  {busy ? (
                    <Loader2 className="spin" size={14} />
                  ) : (
                    <ArrowRight size={14} />
                  )}{" "}
                  Dịch văn bản
                </Button>
              </div>
            </div>
            <div className="mic-area">
              <div className={`waveform ${recording ? "recording" : ""}`}>
                {Array.from({ length: 35 }, (_, i) => (
                  <i
                    key={i}
                    style={{
                      height: recording ? `${7 + ((i * 17) % 28)}px` : "4px",
                      animationDelay: `${i * 0.045}s`,
                    }}
                  />
                ))}
              </div>
              <Button
                className={`mic-button ${recording ? "is-recording" : ""}`}
                disabled={processing && !recording}
                onClick={() => void startMic()}
              >
                {processing && !recording ? (
                  <Loader2 className="spin" size={21} />
                ) : recording ? (
                  <Square size={19} />
                ) : (
                  <Mic size={22} />
                )}
              </Button>
              <strong>{status}</strong>
              <p>
                {recording
                  ? "Nhấn để dừng và hoàn tất đoạn nói"
                  : "Audio được chia cụm khi có khoảng lặng"}
              </p>
              <div className="mic-bottom">
                <label className="toggle-label">
                  <input
                    type="checkbox"
                    checked={tts}
                    disabled={recording}
                    onChange={(e) => setTts(e.target.checked)}
                  />{" "}
                  TTS sau khi dừng micro
                </label>
                <span>
                  <ShieldCheck size={13} /> Không lưu audio gốc
                </span>
              </div>
            </div>
          </section>
          <div className="session-bar">
            <span>
              <Database size={14} />
              {segments.length
                ? lastSaved
                  ? "Đã lưu vào lịch sử"
                  : "Không lưu · theo cài đặt riêng tư"
                : "Lịch sử tuân theo cài đặt riêng tư"}
            </span>
            <button
              disabled={!segments.length}
              onClick={() =>
                download(
                  "avrt-transcript.json",
                  JSON.stringify(segments, null, 2),
                )
              }
            >
              <ArrowDownToLine size={15} /> Xuất hội thoại
            </button>
          </div>
        </div>
        <div className="studio-aside">
          <ResourcePanel report={report} />
          <section className="panel model-panel">
            <div className="panel-title">
              <span>
                <Layers3 size={17} /> Pipeline đang dùng
              </span>
              <Link href="/app/models">
                <Settings2 size={15} />
              </Link>
            </div>
            {[
              ["01", "Nhận dạng giọng nói", asr],
              ["02", "Dịch ngôn ngữ", mt],
              ["03", "Kiểm tra bản dịch", null],
            ].map(([n, label, m]) => (
              <div className="pipeline-row" key={String(n)}>
                <span className="step-number">{String(n)}</span>
                <div>
                  <strong>{String(label)}</strong>
                  <small>
                    {m
                      ? (m as Model).source === "mock"
                        ? "Mock adapter"
                        : (m as Model).model_id
                      : "Quy tắc số & phủ định"}
                  </small>
                </div>
                <Check size={14} />
              </div>
            ))}
            <div className="pipeline-note">
              Kiểm tra quy tắc chưa xác nhận được toàn bộ ý nghĩa của bản dịch.
            </div>
          </section>
          <div className="tip-card">
            <Sparkles size={21} />
            <h3>Mang model của bạn vào.</h3>
            <p>
              Dùng model từ Hugging Face hoặc kết nối trọng số tự huấn luyện qua
              adapter riêng.
            </p>
            <Link href="/app/models">
              Khám phá model <ArrowRight size={14} />
            </Link>
          </div>
        </div>
      </div>
    </>
  );
}
function UploadPage({ report }: { report: (e: unknown) => void }) {
  const [file, setFile] = useState<File | null>(null);
  const [direction, setDirection] = useState("vi-en");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<Segment | null>(null);
  async function send() {
    if (!file) return;
    setBusy(true);
    try {
      const isMp3 =
        file.name.toLowerCase().endsWith(".mp3") || file.type === "audio/mpeg";
      const uploadFile = isMp3 ? await mp3ToWav(file) : file;
      const data = new FormData();
      data.set("file", uploadFile);
      data.set("direction", direction);
      setResult(await api("/translate/upload", { method: "POST", body: data }));
    } catch (e) {
      report(e);
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <PageHead
        eyebrow="AUDIO TRANSLATION"
        title="Từ âm thanh đến ý nghĩa."
        text="Tải WAV hoặc MP3 ngắn để kiểm thử pipeline ASR → MT → kiểm tra quy tắc. MP3 được chuyển đổi trong trình duyệt."
      />
      <section className="panel upload-panel">
        <Upload size={40} />
        <h2>Thêm tệp âm thanh của bạn</h2>
        <p>
          WAV PCM16 mono · 8–48 kHz hoặc MP3 (chuyển đổi trong trình duyệt).
          Giới hạn theo cấu hình backend.
        </p>
        <input
          aria-label="Chọn tệp WAV hoặc MP3"
          type="file"
          accept=".wav,audio/wav,.mp3,audio/mpeg"
          onChange={(e) => setFile(e.target.files?.[0] || null)}
        />
        <select
          aria-label="Chiều dịch"
          value={direction}
          onChange={(e) => setDirection(e.target.value)}
        >
          <option value="en-vi">Anh → Việt</option>
          <option value="vi-en">Việt → Anh</option>
        </select>
        <Button disabled={!file || busy} onClick={() => void send()}>
          {busy ? <Loader2 className="spin" size={16} /> : <Play size={16} />}{" "}
          Dịch tệp
        </Button>
      </section>
      {result && (
        <section className="panel result-panel">
          <Pill tone={result.mock ? "amber" : "green"}>
            {result.mock ? "MOCK" : "ĐÃ XỬ LÝ"}
          </Pill>
          <h3>Bản gốc</h3>
          <p>{result.source_text}</p>
          <h3>Bản dịch</h3>
          <p>{result.target_text}</p>
          {result.verification.warnings.map((w) => (
            <p key={w} className="warning-text">
              {w}
            </p>
          ))}
          <small>
            Tổng thời gian {result.timings.total_ms} ms ·{" "}
            {result.saved ? "Đã lưu" : "Không lưu"}
          </small>
        </section>
      )}
    </>
  );
}
function HistoryPage({ report }: { report: (e: unknown) => void }) {
  const [rows, setRows] = useState<any[]>([]);
  const [detail, setDetail] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const load = () =>
    api("/sessions")
      .then((x) => setRows(x.sessions))
      .catch(report)
      .finally(() => setLoading(false));
  useEffect(() => {
    void load();
  }, []);
  return (
    <>
      <PageHead
        eyebrow="YOUR CONVERSATIONS"
        title="Tiếp nối những câu chuyện."
        text="Xem lại, xuất hoặc xóa các hội thoại của riêng bạn."
      />
      <section className="panel">
        {loading ? (
          <div className="empty">
            <Loader2 className="spin" />
          </div>
        ) : !rows.length ? (
          <Empty
            icon={History}
            title="Chưa có hội thoại nào"
            text="Những bản dịch được cho phép lưu sẽ xuất hiện tại đây."
          />
        ) : (
          <div className="data-table">
            <div className="table-head">
              <span>Hội thoại</span>
              <span>Chiều dịch</span>
              <span>Thời gian</span>
              <span>Thao tác</span>
            </div>
            {rows.map((row) => (
              <div className="table-row" key={row.id}>
                <button
                  className="text-button"
                  onClick={() =>
                    void api(`/sessions/${row.id}`)
                      .then(setDetail)
                      .catch(report)
                  }
                >
                  <strong>{row.preview?.slice(0, 65) || "Hội thoại"}</strong>
                  <small>{row.segment_count} đoạn</small>
                </button>
                <Pill>{row.direction.toUpperCase()}</Pill>
                <span>{new Date(row.created_at).toLocaleString("vi-VN")}</span>
                <div className="row-actions">
                  <button
                    className="icon-button"
                    aria-label="Xuất hội thoại"
                    onClick={() =>
                      void api(`/sessions/${row.id}`)
                        .then((x) =>
                          download(
                            `avrt-${row.id}.json`,
                            JSON.stringify(x, null, 2),
                          ),
                        )
                        .catch(report)
                    }
                  >
                    <ArrowDownToLine size={17} />
                  </button>
                  <button
                    className="icon-button"
                    aria-label="Xóa hội thoại"
                    onClick={() => {
                      if (window.confirm("Xóa vĩnh viễn hội thoại này?"))
                        void api(`/sessions/${row.id}`, { method: "DELETE" })
                          .then(() => {
                            setDetail(null);
                            void load();
                          })
                          .catch(report);
                    }}
                  >
                    <Trash2 size={17} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
      {detail && (
        <section className="panel result-panel">
          <div className="panel-title">
            Chi tiết hội thoại
            <button
              className="icon-button"
              aria-label="Đóng chi tiết"
              onClick={() => setDetail(null)}
            >
              <X size={17} />
            </button>
          </div>
          {detail.segments.map((s: Segment) => (
            <div className="history-segment" key={s.id}>
              <p>{s.source_text}</p>
              <strong>{s.target_text}</strong>
            </div>
          ))}
        </section>
      )}
    </>
  );
}
function ModelsPage({
  user,
  report,
}: {
  user: User;
  report: (e: unknown) => void;
}) {
  const [models, setModels] = useState<Model[]>([]);
  const [worker, setWorker] = useState(false);
  const [busy, setBusy] = useState("");
  const load = () =>
    api("/models")
      .then((x) => {
        setModels(x.models);
        setWorker(x.worker_online);
      })
      .catch(report);
  useEffect(() => {
    void load();
    const timer = setInterval(load, 5000);
    return () => clearInterval(timer);
  }, []);
  return (
    <>
      <PageHead
        eyebrow="OPEN MODEL WORKSPACE"
        title="Model mở. Lựa chọn của bạn."
        text="Cấu hình riêng từng khối ASR, dịch và TTS bằng .env phía server."
      >
        <Pill tone={worker ? "green" : "amber"}>
          {worker ? "Worker sẵn sàng" : "Worker chưa kết nối"}
        </Pill>
      </PageHead>
      <div className="alert info">
        <Layers3 size={18} />
        <span>
          HF Hub tải trọng số về máy chạy. HF Remote gọi dịch vụ bên ngoài.
          Model local cần format tương thích adapter; thay shape không thay đổi
          kiến trúc model.
        </span>
      </div>
      <div className="models-grid">
        {models.map((m) => (
          <section className="panel model-card" key={m.role}>
            <div className="panel-title">
              <span>
                <Layers3 size={17} />
                {m.role}
              </span>
              <Pill tone={m.preflight.ok ? "green" : "amber"}>{m.status}</Pill>
            </div>
            <h3>{m.model_id || "Mock adapter"}</h3>
            <p>
              {m.source === "mock"
                ? "Dữ liệu minh họa để kiểm thử giao diện và luồng API."
                : m.execution === "remote"
                  ? "Inference trên Hugging Face provider."
                  : "Inference local trên máy chạy worker."}
            </p>
            <dl>
              <div>
                <dt>Nguồn</dt>
                <dd>{m.source}</dd>
              </div>
              <div>
                <dt>Thiết bị</dt>
                <dd>{m.device}</dd>
              </div>
              <div>
                <dt>Input shape</dt>
                <dd>{JSON.stringify(m.input_shape)}</dd>
              </div>
              <div>
                <dt>Revision</dt>
                <dd>{m.model_revision || "Chưa pin"}</dd>
              </div>
            </dl>
            <small className={!m.preflight.ok ? "warning-text" : "muted"}>
              {m.preflight.note}
            </small>
            {user.role === "admin" && (
              <Button
                variant="outline"
                size="sm"
                disabled={!!busy || !m.preflight.ok}
                onClick={() => {
                  setBusy(m.role);
                  void api(`/models/${m.role}/warmup`, { method: "POST" })
                    .then(load)
                    .catch(report)
                    .finally(() => setBusy(""));
                }}
              >
                {busy === m.role ? (
                  <Loader2 className="spin" size={14} />
                ) : (
                  <Play size={14} />
                )}{" "}
                Warmup model
              </Button>
            )}
          </section>
        ))}
      </div>
      <div className="panel result-panel">
        <h3>Đưa model tự huấn luyện vào</h3>
        <p>
          Export bằng <code>save_pretrained()</code> với safetensors, đặt trong{" "}
          <code>models/custom/ten-model/</code>, chọn <code>SOURCE=local</code>{" "}
          và adapter phù hợp. Xem hướng dẫn chi tiết ở{" "}
          <code>docs/MODELS.md</code>.
        </p>
      </div>
    </>
  );
}
function MonitorPage({ report }: { report: (e: unknown) => void }) {
  return (
    <>
      <PageHead
        eyebrow="RUNTIME OBSERVABILITY"
        title="Hiệu năng, ngay lúc chạy."
        text="CPU, RAM, GPU và độ trễ từ máy chạy ứng dụng. Không mô phỏng tài nguyên cloud."
      />
      <ResourcePanel wide report={report} />
      <section className="panel result-panel">
        <h3>Đọc đúng số liệu</h3>
        <p>
          CPU và GPU hệ thống có thể bao gồm chương trình khác. Worker được đo
          riêng khi chạy Redis inference. Độ trễ P50/P95 chỉ tổng hợp yêu cầu
          của tài khoản hiện tại, trong cửa sổ gần nhất.
        </p>
        <p>
          Độ trễ này là thời gian inference, chưa bao gồm toàn bộ thời gian
          micro, mạng và phát TTS.
        </p>
      </section>
    </>
  );
}
function BillingPage({
  report,
  reloadUser,
}: {
  report: (e: unknown) => void;
  reloadUser: () => Promise<void>;
}) {
  const [caps, setCaps] = useState<any>(null);
  const [wallet, setWallet] = useState<any>(null);
  const [orders, setOrders] = useState<any[]>([]);
  const [busy, setBusy] = useState(false);
  const key = useRef<string | null>(null);
  const load = () =>
    Promise.all([
      api("/billing/capabilities"),
      api("/billing/wallet"),
      api("/billing/orders"),
    ])
      .then(([c, w, o]) => {
        setCaps(c);
        setWallet(w);
        setOrders(o.orders);
      })
      .catch(report);
  useEffect(() => {
    void load();
    const t = setInterval(load, 5000);
    return () => clearInterval(t);
  }, []);
  async function buy() {
    setBusy(true);
    try {
      key.current = key.current || crypto.randomUUID();
      await api("/billing/orders", {
        method: "POST",
        headers: { "Idempotency-Key": key.current },
      });
      key.current = null;
      await load();
    } catch (e) {
      report(e);
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <PageHead
        eyebrow="BILLING & CREDITS"
        title="Sẵn sàng cho kết nối tiếp theo."
        text="Quản lý ví, tạo đơn và theo dõi thanh toán được xác nhận từ server."
      />
      {caps?.mock && (
        <div className="alert info">
          <CircleHelp size={18} /> Chế độ mock: chỉ mô phỏng credit để kiểm thử,
          không thu tiền thật. Chưa bật trừ credit theo bản dịch.
        </div>
      )}
      <div className="billing-grid">
        <section className="panel wallet-card">
          <div className="eyebrow">SỐ DƯ CREDIT</div>
          <h2>
            {wallet?.balance ?? "—"}
            <small>credits</small>
          </h2>
          <p>Giao dịch được ghi vào sổ cái phía server.</p>
          <Pill tone="green">
            <ShieldCheck size={13} /> MongoDB transaction ready
          </Pill>
        </section>
        <section className="panel package-card">
          <Pill>GÓI NẠP CREDIT</Pill>
          <h2>{caps?.package?.credits ?? "—"} credits</h2>
          <p>
            {caps?.package?.price_vnd?.toLocaleString("vi-VN") || "—"} ₫{" "}
            <small>/ gói</small>
          </p>
          <Button disabled={!caps || busy} onClick={() => void buy()}>
            {busy ? <Loader2 className="spin" size={15} /> : <Plus size={15} />}{" "}
            Tạo đơn {caps?.mock ? "thử nghiệm" : "thanh toán"}
          </Button>
          <small>Google Pay chưa khả dụng · cần PSP tương thích.</small>
        </section>
      </div>
      <section className="panel orders-panel">
        <div className="panel-title">
          <span>
            <Wallet size={17} /> Đơn thanh toán
          </span>
        </div>
        {!orders.length ? (
          <Empty
            icon={Wallet}
            title="Chưa có đơn thanh toán"
            text="Tạo đơn mới để thử luồng thanh toán và ví credit."
          />
        ) : (
          orders.map((o) => (
            <div className="order-row" key={o.id}>
              <div>
                <strong>AVRT{o.order_code}</strong>
                <small>
                  {o.amount_vnd.toLocaleString("vi-VN")} ₫ · {o.credits} credits
                </small>
              </div>
              <Pill tone={o.status === "paid" ? "green" : "amber"}>
                {o.status}
              </Pill>
              {o.checkout_url && (
                <Button variant="outline" size="sm" asChild>
                  <a href={o.checkout_url} target="_blank" rel="noreferrer">
                    Mở QR thanh toán <ArrowRight size={13} />
                  </a>
                </Button>
              )}
              {o.mock && o.status === "pending" && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() =>
                    void api(`/billing/orders/${o.id}/simulate`, {
                      method: "POST",
                    })
                      .then(async () => {
                        await load();
                        await reloadUser();
                      })
                      .catch(report)
                  }
                >
                  Mô phỏng đã nhận tiền
                </Button>
              )}
            </div>
          ))
        )}
      </section>
    </>
  );
}
function SettingsPage({
  user,
  report,
}: {
  user: User;
  report: (e: unknown) => void;
}) {
  const [data, setData] = useState<{
    consent_history: boolean;
    consent_cloud: boolean;
  } | null>(null);
  const [saved, setSaved] = useState(false);
  useEffect(() => {
    void api("/settings").then(setData).catch(report);
  }, []);
  return (
    <>
      <PageHead
        eyebrow="ACCOUNT & PRIVACY"
        title="Dữ liệu của bạn, do bạn chọn."
        text="Quyền riêng tư được áp dụng ở backend cho từng tài khoản."
      />
      <section className="panel settings-panel">
        <h3>Tài khoản</h3>
        <div className="setting-line">
          <span>Email</span>
          <strong>{user.email}</strong>
        </div>
        <div className="setting-line">
          <span>Vai trò</span>
          <Pill>{user.role}</Pill>
        </div>
        <h3>Quyền riêng tư</h3>
        {data && (
          <>
            <label className="setting-line">
              <span>
                <strong>Lưu bản chép lời & bản dịch</strong>
                <small>Cho phép xem lại lịch sử. Không lưu âm thanh gốc.</small>
              </span>
              <input
                type="checkbox"
                checked={data.consent_history}
                onChange={(e) => {
                  setData({ ...data, consent_history: e.target.checked });
                  setSaved(false);
                }}
              />
            </label>
            <label className="setting-line">
              <span>
                <strong>Cho phép gửi dữ liệu lên HF Remote</strong>
                <small>Chỉ áp dụng khi admin cấu hình model dùng cloud.</small>
              </span>
              <input
                type="checkbox"
                checked={data.consent_cloud}
                onChange={(e) => {
                  setData({ ...data, consent_cloud: e.target.checked });
                  setSaved(false);
                }}
              />
            </label>
            <Button
              onClick={() =>
                void api("/settings", {
                  method: "PATCH",
                  body: JSON.stringify(data),
                })
                  .then(() => setSaved(true))
                  .catch(report)
              }
            >
              <Check size={15} />
              {saved ? "Đã lưu cài đặt" : "Lưu cài đặt"}
            </Button>
          </>
        )}
        <p className="muted">
          Speaker Memory, voice cloning và tự huấn luyện chưa được bật trong bản
          này.
        </p>
        {user.role === "admin" && (
          <Link href="/admin">
            Mở nhật ký quản trị <ArrowRight size={14} />
          </Link>
        )}
      </section>
    </>
  );
}
function AdminPage({ report }: { report: (e: unknown) => void }) {
  const [events, setEvents] = useState<any[]>([]);
  useEffect(() => {
    void api("/admin/audit")
      .then((x) => setEvents(x.events))
      .catch(report);
  }, []);
  return (
    <>
      <PageHead
        eyebrow="ADMINISTRATION"
        title="Nhật ký quản trị."
        text="Mọi thao tác kiểm tra quyền ở backend."
      />
      <section className="panel result-panel">
        {events.map((e) => (
          <div className="setting-line" key={e.id}>
            <strong>{e.action}</strong>
            <small>{new Date(e.created_at).toLocaleString("vi-VN")}</small>
          </div>
        ))}
      </section>
    </>
  );
}
