import { useState, useEffect, useRef, useCallback } from "react";
import "@/App.css";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import axios from "axios";
import { Panel, PanelGroup, PanelResizeHandle } from "react-resizable-panels";
import { motion, AnimatePresence } from "framer-motion";
import { 
  TerminalSquare, 
  Smartphone, 
  Hammer, 
  Settings, 
  ScrollText, 
  Cpu,
  ChevronUp,
  ChevronDown,
  Send,
  Play,
  RefreshCw,
  Info,
  Zap,
  HardDrive,
  Layers,
  Bot,
  Loader2,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Copy,
  Trash2,
  Download
} from "lucide-react";
import { Toaster, toast } from "sonner";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// ======================= COMPONENTS =======================

const Logo = () => (
  <div className="flex items-center gap-3">
    <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-[#E95420] to-[#77216F] flex items-center justify-center ubuntu-glow">
      <Layers className="w-5 h-5 text-white" />
    </div>
    <div>
      <h1 className="text-lg font-bold text-white tracking-tight font-['Ubuntu']">Halium Builder</h1>
      <p className="text-xs text-white/50">AI-Powered Linux Porting</p>
    </div>
  </div>
);

const Badge = ({ variant = "neutral", children }) => {
  const variants = {
    success: "badge-success",
    warning: "badge-warning",
    error: "badge-error",
    neutral: "badge-neutral"
  };
  return <span className={`badge ${variants[variant]}`}>{children}</span>;
};

const ProgressBlocks = ({ progress, total = 10 }) => {
  const filled = Math.round((progress / 100) * total);
  const empty = total - filled;
  return (
    <span className="progress-blocks text-sm">
      [<span className="text-[#E95420]">{"█".repeat(filled)}</span>
      <span className="text-white/20">{"░".repeat(empty)}</span>]
    </span>
  );
};

const DeviceCard = ({ device, isSelected, onSelect, onRefresh }) => {
  const [loading, setLoading] = useState(false);
  const [info, setInfo] = useState(null);

  const fetchInfo = useCallback(async () => {
    if (!device?.serial) return;
    setLoading(true);
    try {
      const res = await axios.get(`${API}/devices/${device.serial}/info`);
      setInfo(res.data);
    } catch (e) {
      console.error("Failed to fetch device info:", e);
    } finally {
      setLoading(false);
    }
  }, [device?.serial]);

  useEffect(() => {
    if (device?.state === "device") {
      fetchInfo();
    }
  }, [device, fetchInfo]);

  if (!device) {
    return (
      <div className="glass-card rounded-xl p-6 flex flex-col items-center justify-center min-h-[200px]">
        <Smartphone className="w-12 h-12 text-white/20 mb-3" />
        <p className="text-white/40 text-sm">No device connected</p>
        <p className="text-white/30 text-xs mt-1">Connect via USB and enable ADB</p>
      </div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className={`glass-card rounded-xl p-5 cursor-pointer transition-all ${isSelected ? "glass-card-active" : ""}`}
      onClick={() => onSelect(device)}
      data-testid="device-card"
    >
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${device.state === "device" ? "bg-[#0E8420]/20" : "bg-[#F99B11]/20"}`}>
            <Smartphone className={`w-5 h-5 ${device.state === "device" ? "text-[#38D878]" : "text-[#F99B11]"}`} />
          </div>
          <div>
            <h3 className="font-semibold text-white">{info?.model || device.serial}</h3>
            <p className="text-xs text-white/50">{device.serial}</p>
          </div>
        </div>
        <Badge variant={device.state === "device" ? "success" : "warning"}>
          {device.state}
        </Badge>
      </div>

      {loading ? (
        <div className="flex items-center gap-2 text-white/40 text-sm">
          <Loader2 className="w-4 h-4 animate-spin" />
          Loading device info...
        </div>
      ) : info ? (
        <div className="space-y-2 text-sm">
          <div className="flex justify-between">
            <span className="text-white/50">Device</span>
            <span className="text-white/80 font-mono">{info.device || "N/A"}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-white/50">Manufacturer</span>
            <span className="text-white/80">{info.manufacturer || "N/A"}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-white/50">Android</span>
            <span className="text-white/80">{info.android_version || "N/A"}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-white/50">CPU ABI</span>
            <span className="text-white/80 font-mono text-xs">{info.cpu_abi || "N/A"}</span>
          </div>
        </div>
      ) : null}

      <div className="mt-4 pt-3 border-t border-white/5 flex gap-2">
        <button
          onClick={(e) => { e.stopPropagation(); fetchInfo(); }}
          className="btn-outline text-xs py-1.5 px-3 flex items-center gap-1.5"
          data-testid="refresh-device-btn"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          Refresh
        </button>
        <button
          onClick={(e) => { e.stopPropagation(); onRefresh(); }}
          className="btn-outline text-xs py-1.5 px-3 flex items-center gap-1.5"
          data-testid="scan-devices-btn"
        >
          <HardDrive className="w-3.5 h-3.5" />
          Scan All
        </button>
      </div>
    </motion.div>
  );
};

const BuildStatusCard = ({ session }) => {
  const getStepIcon = (status) => {
    switch (status) {
      case "completed": return <CheckCircle2 className="w-4 h-4 text-[#38D878]" />;
      case "running": return <Loader2 className="w-4 h-4 text-[#E95420] animate-spin" />;
      case "failed": return <XCircle className="w-4 h-4 text-[#C7162B]" />;
      default: return <AlertCircle className="w-4 h-4 text-white/30" />;
    }
  };

  if (!session) {
    return (
      <div className="glass-card rounded-xl p-6 flex flex-col items-center justify-center min-h-[200px]">
        <Hammer className="w-12 h-12 text-white/20 mb-3" />
        <p className="text-white/40 text-sm">No active build</p>
        <p className="text-white/30 text-xs mt-1">Start a build to see progress</p>
      </div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="glass-card rounded-xl p-5"
      data-testid="build-status-card"
    >
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold text-white flex items-center gap-2">
          <Hammer className="w-4 h-4 text-[#E95420]" />
          Build Status
        </h3>
        <Badge variant={session.status === "completed" ? "success" : session.status === "failed" ? "error" : "warning"}>
          {session.status}
        </Badge>
      </div>

      <div className="mb-4">
        <div className="flex justify-between text-sm mb-2">
          <span className="text-white/50">Progress</span>
          <span className="text-white/80">{session.progress}%</span>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex-1 h-2 bg-black/30 rounded-full overflow-hidden">
            <motion.div
              className="h-full bg-gradient-to-r from-[#E95420] to-[#77216F]"
              initial={{ width: 0 }}
              animate={{ width: `${session.progress}%` }}
              transition={{ duration: 0.5 }}
            />
          </div>
          <ProgressBlocks progress={session.progress} />
        </div>
      </div>

      <div className="space-y-2">
        <div className="flex items-center gap-2 text-sm">
          {getStepIcon(session.status)}
          <span className="text-white/80">{session.current_step || "Initializing..."}</span>
        </div>
        <div className="text-xs text-white/40">
          Device: {session.device_codename || session.device_serial}
        </div>
        <div className="text-xs text-white/40">
          Halium: {session.halium_version}
        </div>
      </div>
    </motion.div>
  );
};

const HaliumVersionSelector = ({ selected, onSelect, versions }) => (
  <div className="glass-card rounded-xl p-5" data-testid="halium-version-selector">
    <h3 className="font-semibold text-white flex items-center gap-2 mb-4">
      <Cpu className="w-4 h-4 text-[#E95420]" />
      Halium Version
    </h3>
    <div className="grid grid-cols-2 gap-2">
      {versions.map((v) => (
        <button
          key={v.id}
          onClick={() => onSelect(v.id)}
          className={`p-3 rounded-lg text-left transition-all ${
            selected === v.id
              ? "bg-[#E95420]/20 border border-[#E95420]/50"
              : "bg-black/20 border border-white/5 hover:border-white/10"
          }`}
          data-testid={`halium-version-${v.id}`}
        >
          <div className="font-medium text-sm text-white">{v.name}</div>
          <div className="text-xs text-white/40">{v.android_base}</div>
          <Badge variant={v.status === "latest" ? "success" : "neutral"} className="mt-2">
            {v.status}
          </Badge>
        </button>
      ))}
    </div>
  </div>
);

const Terminal = ({ history, onCommand, isLoading }) => {
  const [input, setInput] = useState("");
  const terminalRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    if (terminalRef.current) {
      terminalRef.current.scrollTop = terminalRef.current.scrollHeight;
    }
  }, [history]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (input.trim() && !isLoading) {
      onCommand(input.trim());
      setInput("");
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "ArrowUp") {
      // TODO: Command history navigation
    }
  };

  return (
    <div className="flex flex-col h-full bg-[#0A0A0A] rounded-lg overflow-hidden" data-testid="terminal">
      <div className="flex items-center justify-between px-4 py-2 bg-black/50 border-b border-white/5">
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-[#C7162B]" />
          <div className="w-3 h-3 rounded-full bg-[#F99B11]" />
          <div className="w-3 h-3 rounded-full bg-[#0E8420]" />
        </div>
        <span className="text-xs text-white/40 font-mono">halium-terminal</span>
      </div>

      <div
        ref={terminalRef}
        className="flex-1 overflow-y-auto p-4 font-mono text-sm space-y-2"
      >
        {history.map((entry, i) => (
          <div key={i} className="animate-fade-in">
            {entry.type === "command" && (
              <div className="flex gap-2">
                <span className="terminal-prompt">❯</span>
                <span className="terminal-command">{entry.content}</span>
              </div>
            )}
            {entry.type === "output" && (
              <pre className="terminal-output whitespace-pre-wrap pl-4">{entry.content}</pre>
            )}
            {entry.type === "error" && (
              <pre className="terminal-error whitespace-pre-wrap pl-4">{entry.content}</pre>
            )}
            {entry.type === "ai" && (
              <div className="pl-4 text-white/60 border-l-2 border-[#77216F] ml-2">
                <span className="text-[#77216F] text-xs">// AI:</span>
                <div className="ai-message mt-1">{entry.content}</div>
              </div>
            )}
          </div>
        ))}
        {isLoading && (
          <div className="flex items-center gap-2 text-white/40">
            <Loader2 className="w-4 h-4 animate-spin" />
            <span>Executing...</span>
          </div>
        )}
      </div>

      <form onSubmit={handleSubmit} className="p-3 border-t border-white/5 bg-black/30">
        <div className="flex items-center gap-2">
          <span className="terminal-prompt">❯</span>
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Enter command..."
            className="flex-1 bg-transparent outline-none text-[#38D878] font-mono placeholder:text-white/20"
            disabled={isLoading}
            data-testid="terminal-input"
          />
          <button
            type="submit"
            disabled={isLoading || !input.trim()}
            className="p-2 rounded hover:bg-white/5 text-white/40 hover:text-white disabled:opacity-30"
            data-testid="terminal-submit"
          >
            <Play className="w-4 h-4" />
          </button>
        </div>
      </form>
    </div>
  );
};

const AIChat = ({ messages, onSend, isLoading, deviceContext }) => {
  const [input, setInput] = useState("");
  const [autoExecute, setAutoExecute] = useState(false);
  const chatRef = useRef(null);

  useEffect(() => {
    if (chatRef.current) {
      chatRef.current.scrollTop = chatRef.current.scrollHeight;
    }
  }, [messages]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (input.trim() && !isLoading) {
      onSend(input.trim(), autoExecute);
      setInput("");
    }
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    toast.success("Copied to clipboard");
  };

  const formatMessage = (content) => {
    // Simple markdown-like formatting
    const parts = content.split(/(```[\s\S]*?```)/g);
    return parts.map((part, i) => {
      if (part.startsWith("```") && part.endsWith("```")) {
        const code = part.slice(3, -3).replace(/^(bash|sh|shell)\n/, "");
        return (
          <div key={i} className="relative group my-2">
            <pre className="bg-black/40 border border-white/10 rounded-lg p-4 overflow-x-auto">
              <code className="text-[#38D878] text-sm">{code}</code>
            </pre>
            <button
              onClick={() => copyToClipboard(code)}
              className="absolute top-2 right-2 p-1.5 rounded bg-white/5 opacity-0 group-hover:opacity-100 transition-opacity"
            >
              <Copy className="w-3.5 h-3.5 text-white/60" />
            </button>
          </div>
        );
      }
      return <span key={i} className="whitespace-pre-wrap">{part}</span>;
    });
  };

  return (
    <div className="flex flex-col h-full" data-testid="ai-chat">
      <div className="px-4 py-3 border-b border-white/5 bg-[#2C001E]/30 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Bot className="w-5 h-5 text-[#E95420]" />
          <span className="font-semibold text-white">AI Assistant</span>
          <Badge variant="neutral">Claude 4.5</Badge>
        </div>
        <label className="flex items-center gap-2 text-xs cursor-pointer">
          <input
            type="checkbox"
            checked={autoExecute}
            onChange={(e) => setAutoExecute(e.target.checked)}
            className="accent-[#E95420]"
          />
          <span className="text-white/50">Auto-execute commands</span>
        </label>
      </div>

      <div ref={chatRef} className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="text-center py-8">
            <Bot className="w-12 h-12 text-white/20 mx-auto mb-3" />
            <p className="text-white/40 text-sm">Ask me about Halium porting, device analysis, or build troubleshooting</p>
            <div className="mt-4 flex flex-wrap gap-2 justify-center">
              {["Analyze my device for Halium", "What Halium version should I use?", "Check device compatibility"].map((q) => (
                <button
                  key={q}
                  onClick={() => { setInput(q); }}
                  className="text-xs px-3 py-1.5 rounded-full bg-white/5 text-white/60 hover:bg-white/10 hover:text-white transition-all"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg, i) => (
          <motion.div
            key={i}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className={`${msg.role === "user" ? "ml-8" : "mr-8"}`}
          >
            <div className={`rounded-xl p-4 ${
              msg.role === "user"
                ? "bg-[#E95420]/20 border border-[#E95420]/30"
                : "bg-black/30 border border-white/5"
            }`}>
              <div className="flex items-center gap-2 mb-2">
                {msg.role === "assistant" ? (
                  <Bot className="w-4 h-4 text-[#77216F]" />
                ) : (
                  <span className="text-[#E95420] text-xs font-mono">you@halium</span>
                )}
                <span className="text-xs text-white/30">
                  {new Date(msg.timestamp).toLocaleTimeString()}
                </span>
              </div>
              <div className="ai-message">
                {formatMessage(msg.content)}
              </div>
              {msg.extracted_commands?.length > 0 && (
                <div className="mt-3 pt-3 border-t border-white/5">
                  <span className="text-xs text-white/40">Extracted commands:</span>
                  <div className="mt-2 space-y-1">
                    {msg.extracted_commands.map((cmd, j) => (
                      <div key={j} className="flex items-center gap-2 text-xs font-mono bg-black/20 rounded px-2 py-1">
                        <Play className="w-3 h-3 text-[#38D878]" />
                        <span className="text-[#38D878]">{cmd}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </motion.div>
        ))}

        {isLoading && (
          <div className="flex items-center gap-2 text-white/40 p-4">
            <Loader2 className="w-4 h-4 animate-spin" />
            <span className="text-sm">AI is thinking...</span>
          </div>
        )}
      </div>

      <form onSubmit={handleSubmit} className="p-4 border-t border-white/5 bg-black/20">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about Halium porting..."
            className="input-dark flex-1"
            disabled={isLoading}
            data-testid="ai-chat-input"
          />
          <button
            type="submit"
            disabled={isLoading || !input.trim()}
            className="btn-primary flex items-center gap-2"
            data-testid="ai-chat-submit"
          >
            <Send className="w-4 h-4" />
            Send
          </button>
        </div>
        {deviceContext && (
          <p className="text-xs text-white/30 mt-2">
            Device context: {deviceContext.model || deviceContext.serial} will be included
          </p>
        )}
      </form>
    </div>
  );
};

const LogViewer = ({ logs }) => (
  <div className="glass-card rounded-xl p-5 h-full flex flex-col" data-testid="log-viewer">
    <div className="flex items-center justify-between mb-4">
      <h3 className="font-semibold text-white flex items-center gap-2">
        <ScrollText className="w-4 h-4 text-[#E95420]" />
        Recent Logs
      </h3>
      <button className="text-white/40 hover:text-white p-1.5 rounded hover:bg-white/5">
        <Download className="w-4 h-4" />
      </button>
    </div>
    <div className="flex-1 overflow-y-auto font-mono text-xs space-y-1 bg-black/20 rounded-lg p-3">
      {logs.length === 0 ? (
        <p className="text-white/30 text-center py-4">No logs yet</p>
      ) : (
        logs.map((log, i) => (
          <div key={i} className={`${log.type === "error" ? "text-[#C7162B]" : "text-white/60"}`}>
            <span className="text-white/30">[{log.timestamp}]</span> {log.message}
          </div>
        ))
      )}
    </div>
  </div>
);

// ======================= MAIN DASHBOARD =======================

const Dashboard = () => {
  const [devices, setDevices] = useState([]);
  const [selectedDevice, setSelectedDevice] = useState(null);
  const [deviceInfo, setDeviceInfo] = useState(null);
  const [buildSession, setBuildSession] = useState(null);
  const [haliumVersions, setHaliumVersions] = useState([]);
  const [selectedVersion, setSelectedVersion] = useState("halium-11.0");
  const [terminalHistory, setTerminalHistory] = useState([]);
  const [chatMessages, setChatMessages] = useState([]);
  const [logs, setLogs] = useState([]);
  const [isTerminalLoading, setIsTerminalLoading] = useState(false);
  const [isAiLoading, setIsAiLoading] = useState(false);
  const [terminalExpanded, setTerminalExpanded] = useState(true);
  const [sessionId] = useState(() => `session-${Date.now()}`);

  // Fetch initial data
  useEffect(() => {
    fetchDevices();
    fetchHaliumVersions();
    checkHealth();
  }, []);

  const checkHealth = async () => {
    try {
      const res = await axios.get(`${API}/health`);
      if (!res.data.tools.adb) {
        addLog("warning", "ADB not detected on system");
      } else {
        addLog("info", "System ready - ADB available");
      }
    } catch (e) {
      addLog("error", "Failed to connect to backend");
    }
  };

  const fetchDevices = async () => {
    try {
      const res = await axios.get(`${API}/devices`);
      setDevices(res.data.devices);
      if (res.data.devices.length > 0) {
        addLog("info", `Found ${res.data.devices.length} device(s)`);
      }
    } catch (e) {
      addLog("error", "Failed to fetch devices");
    }
  };

  const fetchHaliumVersions = async () => {
    try {
      const res = await axios.get(`${API}/halium/versions`);
      setHaliumVersions(res.data.versions);
    } catch (e) {
      console.error("Failed to fetch Halium versions:", e);
    }
  };

  const fetchDeviceInfo = async (serial) => {
    try {
      const res = await axios.get(`${API}/devices/${serial}/info`);
      setDeviceInfo(res.data);
      return res.data;
    } catch (e) {
      console.error("Failed to fetch device info:", e);
      return null;
    }
  };

  const addLog = (type, message) => {
    setLogs((prev) => [...prev.slice(-99), {
      type,
      message,
      timestamp: new Date().toLocaleTimeString()
    }]);
  };

  const handleDeviceSelect = async (device) => {
    setSelectedDevice(device);
    if (device?.state === "device") {
      const info = await fetchDeviceInfo(device.serial);
      if (info) {
        addLog("info", `Selected device: ${info.model || device.serial}`);
        setTerminalHistory((prev) => [...prev, {
          type: "ai",
          content: `Device selected: ${info.model} (${info.device})\nAndroid ${info.android_version} | ${info.cpu_abi}`
        }]);
      }
    }
  };

  const handleTerminalCommand = async (command) => {
    setIsTerminalLoading(true);
    setTerminalHistory((prev) => [...prev, { type: "command", content: command }]);

    try {
      const res = await axios.post(`${API}/terminal/execute`, {
        command,
        session_id: sessionId
      });

      if (res.data.stdout) {
        setTerminalHistory((prev) => [...prev, { type: "output", content: res.data.stdout }]);
      }
      if (res.data.stderr) {
        setTerminalHistory((prev) => [...prev, { type: "error", content: res.data.stderr }]);
      }

      addLog(res.data.success ? "info" : "error", `Command: ${command} (exit: ${res.data.exit_code})`);
    } catch (e) {
      setTerminalHistory((prev) => [...prev, { type: "error", content: e.message }]);
      addLog("error", `Command failed: ${command}`);
    } finally {
      setIsTerminalLoading(false);
    }
  };

  const handleAiChat = async (message, autoExecute) => {
    setIsAiLoading(true);
    
    // Add user message immediately
    const userMsg = {
      role: "user",
      content: message,
      timestamp: new Date().toISOString()
    };
    setChatMessages((prev) => [...prev, userMsg]);

    try {
      const res = await axios.post(`${API}/ai/chat`, {
        message,
        session_id: sessionId,
        device_context: deviceInfo,
        auto_execute: autoExecute
      });

      const assistantMsg = {
        role: "assistant",
        content: res.data.response,
        extracted_commands: res.data.extracted_commands,
        timestamp: new Date().toISOString()
      };
      setChatMessages((prev) => [...prev, assistantMsg]);

      // If auto-execute was on and there were commands
      if (autoExecute && res.data.extracted_commands?.length > 0) {
        for (const cmd of res.data.extracted_commands) {
          await handleTerminalCommand(cmd);
        }
      }

      addLog("info", "AI response received");
    } catch (e) {
      toast.error("AI chat failed: " + e.message);
      addLog("error", "AI chat failed");
    } finally {
      setIsAiLoading(false);
    }
  };

  const handleStartBuild = async () => {
    if (!selectedDevice?.serial) {
      toast.error("Please select a device first");
      return;
    }

    try {
      const res = await axios.post(`${API}/build/start`, {
        device_serial: selectedDevice.serial,
        halium_version: selectedVersion,
        build_type: "lineage",
        auto_mode: true
      });
      setBuildSession(res.data);
      addLog("info", `Build started for ${res.data.device_codename || selectedDevice.serial}`);
      toast.success("Build session started");
    } catch (e) {
      toast.error("Failed to start build");
      addLog("error", "Failed to start build");
    }
  };

  return (
    <div className="min-h-screen flex flex-col" data-testid="dashboard">
      {/* Header */}
      <header className="px-6 py-4 border-b border-white/5 bg-gradient-to-r from-[#2C001E]/50 to-transparent">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <Logo />
          <div className="flex items-center gap-4">
            <button
              onClick={fetchDevices}
              className="btn-outline text-sm flex items-center gap-2"
              data-testid="refresh-devices-btn"
            >
              <RefreshCw className="w-4 h-4" />
              Refresh Devices
            </button>
            <button
              onClick={handleStartBuild}
              className="btn-primary flex items-center gap-2"
              disabled={!selectedDevice}
              data-testid="start-build-btn"
            >
              <Zap className="w-4 h-4" />
              Start Build
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 flex flex-col">
        <PanelGroup direction="vertical">
          {/* Dashboard Panel */}
          <Panel defaultSize={60} minSize={30}>
            <div className="h-full overflow-auto p-6">
              <div className="max-w-7xl mx-auto">
                {/* Bento Grid */}
                <div className="grid grid-cols-12 gap-4">
                  {/* Device Panel - Large */}
                  <div className="col-span-12 lg:col-span-5">
                    <h2 className="text-lg font-semibold text-white mb-3 flex items-center gap-2">
                      <Smartphone className="w-5 h-5 text-[#E95420]" />
                      Connected Devices
                    </h2>
                    <div className="space-y-3">
                      {devices.length === 0 ? (
                        <DeviceCard device={null} onRefresh={fetchDevices} />
                      ) : (
                        devices.map((d) => (
                          <DeviceCard
                            key={d.serial}
                            device={d}
                            isSelected={selectedDevice?.serial === d.serial}
                            onSelect={handleDeviceSelect}
                            onRefresh={fetchDevices}
                          />
                        ))
                      )}
                    </div>
                  </div>

                  {/* Right Column */}
                  <div className="col-span-12 lg:col-span-7 space-y-4">
                    {/* Build Status - Medium */}
                    <BuildStatusCard session={buildSession} />

                    {/* Version Selector */}
                    <HaliumVersionSelector
                      selected={selectedVersion}
                      onSelect={setSelectedVersion}
                      versions={haliumVersions}
                    />

                    {/* Logs - Tall */}
                    <LogViewer logs={logs} />
                  </div>
                </div>
              </div>
            </div>
          </Panel>

          {/* Resize Handle */}
          <PanelResizeHandle className="h-2 bg-transparent hover:bg-[#E95420]/30 transition-colors cursor-row-resize flex items-center justify-center group">
            <div className="w-12 h-1 rounded-full bg-white/10 group-hover:bg-[#E95420]/50 transition-colors" />
          </PanelResizeHandle>

          {/* Terminal/AI Panel */}
          <Panel defaultSize={40} minSize={20} collapsible>
            <div className="h-full flex flex-col bg-[#0A0A0A] border-t border-white/5">
              {/* Panel Header */}
              <div className="flex items-center justify-between px-4 py-2 bg-black/50 border-b border-white/5">
                <div className="flex items-center gap-4">
                  <button
                    className={`flex items-center gap-2 px-3 py-1.5 rounded text-sm transition-all ${
                      terminalExpanded ? "bg-[#E95420]/20 text-[#E95420]" : "text-white/50 hover:text-white"
                    }`}
                    onClick={() => setTerminalExpanded(true)}
                  >
                    <TerminalSquare className="w-4 h-4" />
                    Terminal
                  </button>
                  <button
                    className={`flex items-center gap-2 px-3 py-1.5 rounded text-sm transition-all ${
                      !terminalExpanded ? "bg-[#77216F]/20 text-[#77216F]" : "text-white/50 hover:text-white"
                    }`}
                    onClick={() => setTerminalExpanded(false)}
                  >
                    <Bot className="w-4 h-4" />
                    AI Chat
                  </button>
                </div>
                <button
                  className="text-white/40 hover:text-white p-1"
                  onClick={() => {
                    if (terminalExpanded) {
                      setTerminalHistory([]);
                    } else {
                      setChatMessages([]);
                    }
                  }}
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>

              {/* Panel Content */}
              <div className="flex-1 overflow-hidden">
                <AnimatePresence mode="wait">
                  {terminalExpanded ? (
                    <motion.div
                      key="terminal"
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      exit={{ opacity: 0 }}
                      className="h-full"
                    >
                      <Terminal
                        history={terminalHistory}
                        onCommand={handleTerminalCommand}
                        isLoading={isTerminalLoading}
                      />
                    </motion.div>
                  ) : (
                    <motion.div
                      key="chat"
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      exit={{ opacity: 0 }}
                      className="h-full"
                    >
                      <AIChat
                        messages={chatMessages}
                        onSend={handleAiChat}
                        isLoading={isAiLoading}
                        deviceContext={deviceInfo}
                      />
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            </div>
          </Panel>
        </PanelGroup>
      </main>

      <Toaster 
        position="bottom-right" 
        toastOptions={{
          style: {
            background: '#2C2025',
            color: '#F5F5F5',
            border: '1px solid rgba(255,255,255,0.1)',
          },
        }}
      />
    </div>
  );
};

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/*" element={<Dashboard />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
