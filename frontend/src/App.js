import { useState, useEffect, useRef, useCallback } from "react";
import "@/App.css";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import axios from "axios";
import { Panel, Group as PanelGroup, Separator as PanelResizeHandle } from "react-resizable-panels";
import { motion, AnimatePresence } from "framer-motion";
import { 
  TerminalSquare, Smartphone, Hammer, Settings, ScrollText, Cpu, Send, Play, RefreshCw, 
  Info, Zap, HardDrive, Layers, Bot, Loader2, CheckCircle2, XCircle, AlertCircle, 
  Copy, Trash2, Download, Upload, GitBranch, Package, Wrench, Monitor, Server,
  ChevronRight, ChevronDown, FileCode, Cog, Box, Database, Shield, Wifi, Battery,
  CircuitBoard, Binary, FolderGit2, Target, ArrowUpCircle, CheckCheck, XOctagon,
  MessageSquare, Sparkles, Gauge, Lock, Palette, Volume2, Camera, Rocket
} from "lucide-react";
import { Toaster, toast } from "sonner";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// ======================= COMPONENTS =======================

const Logo = () => (
  <div className="flex items-center gap-3">
    <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-[#E95420] to-[#77216F] flex items-center justify-center ubuntu-glow">
      <CircuitBoard className="w-5 h-5 text-white" />
    </div>
    <div>
      <h1 className="text-lg font-bold text-white tracking-tight font-['Ubuntu']">Linux Device Forge</h1>
      <p className="text-xs text-white/50">Kernel • OS • Android • Halium</p>
    </div>
  </div>
);

const Badge = ({ variant = "neutral", children, className = "" }) => {
  const variants = {
    success: "badge-success",
    warning: "badge-warning",
    error: "badge-error",
    neutral: "badge-neutral",
    primary: "bg-[#E95420]/20 text-[#E95420] border border-[#E95420]/30",
    android: "bg-[#3DDC84]/20 text-[#3DDC84] border border-[#3DDC84]/30"
  };
  return <span className={`badge ${variants[variant]} ${className}`}>{children}</span>;
};

const ToolTab = ({ icon: Icon, label, active, onClick, badge, color }) => (
  <button
    onClick={onClick}
    className={`flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-all ${
      active
        ? `bg-${color || '[#E95420]'}/20 text-${color || '[#E95420]'} border border-${color || '[#E95420]'}/30`
        : "text-white/60 hover:text-white hover:bg-white/5"
    }`}
    style={active && color ? { backgroundColor: `${color}20`, color: color, borderColor: `${color}50` } : {}}
    data-testid={`tool-tab-${label.toLowerCase().replace(/\s/g, '-')}`}
  >
    <Icon className="w-4 h-4" />
    {label}
    {badge && <Badge variant="neutral" className="ml-1 text-[10px]">{badge}</Badge>}
  </button>
);

const InterviewDepthCard = ({ depth, info, selected, onSelect }) => (
  <motion.div
    whileHover={{ scale: 1.02 }}
    onClick={() => onSelect(depth)}
    className={`p-4 rounded-xl cursor-pointer transition-all ${
      selected
        ? "bg-[#3DDC84]/20 border-2 border-[#3DDC84]/50"
        : "glass-card hover:border-white/20"
    }`}
    data-testid={`depth-${depth}`}
  >
    <div className="flex items-center gap-3 mb-2">
      <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
        depth === "quick" ? "bg-green-500/20" : depth === "standard" ? "bg-blue-500/20" : "bg-purple-500/20"
      }`}>
        {depth === "quick" ? <Rocket className="w-5 h-5 text-green-400" /> :
         depth === "standard" ? <Gauge className="w-5 h-5 text-blue-400" /> :
         <Sparkles className="w-5 h-5 text-purple-400" />}
      </div>
      <div>
        <h4 className="font-semibold text-white">{info.name}</h4>
        <Badge variant="neutral" className="text-[9px]">{info.questions_count} questions</Badge>
      </div>
    </div>
    <p className="text-xs text-white/50">{info.description}</p>
  </motion.div>
);

const DistroCard = ({ distro, info, selected, onSelect }) => (
  <motion.div
    whileHover={{ scale: 1.02 }}
    onClick={() => onSelect(distro)}
    className={`p-4 rounded-xl cursor-pointer transition-all ${
      selected ? "bg-[#E95420]/20 border-2 border-[#E95420]/50" : "glass-card hover:border-white/20"
    }`}
  >
    <div className="flex items-center gap-3 mb-2">
      <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${
        info.type === "mobile" ? "bg-purple-500/20" : "bg-blue-500/20"
      }`}>
        {info.type === "mobile" ? <Smartphone className="w-4 h-4 text-purple-400" /> : <Monitor className="w-4 h-4 text-blue-400" />}
      </div>
      <div>
        <h4 className="font-semibold text-white text-sm">{info.name}</h4>
        <Badge variant={info.type === "mobile" ? "primary" : "neutral"} className="text-[9px]">{info.type}</Badge>
      </div>
    </div>
    <p className="text-xs text-white/50 line-clamp-2">{info.description}</p>
  </motion.div>
);

// ======================= APP COMPILER MODAL =======================

const AppCompilerModal = ({ show, onClose }) => {
  const [platforms, setPlatforms] = useState({});
  const [aiProviders, setAiProviders] = useState({});
  const [selectedPlatform, setSelectedPlatform] = useState("linux_appimage");
  const [selectedProvider, setSelectedProvider] = useState("emergent");
  const [selectedModel, setSelectedModel] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [compiling, setCompiling] = useState(false);
  const [result, setResult] = useState(null);

  useEffect(() => {
    if (show) {
      fetchPlatforms();
    }
  }, [show]);

  const fetchPlatforms = async () => {
    try {
      const res = await axios.get(`${API}/compiler/platforms`);
      setPlatforms(res.data.platforms);
      setAiProviders(res.data.ai_providers);
      if (res.data.ai_providers.emergent) {
        setSelectedModel(res.data.ai_providers.emergent.models[0]);
      }
    } catch (e) {
      toast.error("Failed to fetch platforms");
    }
  };

  const handleProviderChange = (provider) => {
    setSelectedProvider(provider);
    if (aiProviders[provider]?.models?.length > 0) {
      setSelectedModel(aiProviders[provider].models[0]);
    }
  };

  const compileApp = async () => {
    setCompiling(true);
    setResult(null);
    try {
      const res = await axios.post(`${API}/compiler/compile`, {
        platform: selectedPlatform,
        ai_config: {
          provider: selectedProvider,
          model: selectedModel,
          api_key: selectedProvider !== "emergent" && !aiProviders[selectedProvider]?.local ? apiKey : undefined
        }
      });
      setResult(res.data);
      toast.success("App compiled successfully!");
    } catch (e) {
      toast.error(e.response?.data?.detail || "Compilation failed");
    } finally {
      setCompiling(false);
    }
  };

  if (!show) return null;

  const currentProvider = aiProviders[selectedProvider] || {};
  const currentPlatform = platforms[selectedPlatform] || {};

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm" onClick={onClose}>
      <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }}
        onClick={(e) => e.stopPropagation()}
        className="glass-card rounded-2xl p-6 max-w-4xl w-full mx-4 max-h-[85vh] overflow-y-auto">
        
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-bold text-white flex items-center gap-2">
            <Download className="w-7 h-7 text-[#E95420]" />
            Compile Local App
          </h2>
          <button onClick={onClose} className="text-white/50 hover:text-white">
            <XCircle className="w-6 h-6" />
          </button>
        </div>

        <p className="text-sm text-white/60 mb-6">
          Convert this web app into a standalone desktop or mobile application that runs completely on your machine. Choose your platform, configure AI provider, and download!
        </p>

        {/* Platform Selection */}
        <div className="mb-6">
          <h3 className="text-lg font-semibold text-white mb-3 flex items-center gap-2">
            <Monitor className="w-5 h-5 text-[#E95420]" /> Select Platform
          </h3>
          <div className="grid grid-cols-2 gap-3">
            {Object.entries(platforms).map(([key, info]) => (
              <motion.div key={key} whileHover={{ scale: 1.02 }}
                onClick={() => setSelectedPlatform(key)}
                className={`p-4 rounded-xl cursor-pointer transition-all ${
                  selectedPlatform === key ? "bg-[#E95420]/20 border-2 border-[#E95420]/50" : "bg-black/30 border border-white/5"
                }`}>
                <div className="flex items-center gap-2 mb-2">
                  {key.includes('android') ? <Smartphone className="w-5 h-5 text-[#3DDC84]" /> : <Monitor className="w-5 h-5 text-blue-400" />}
                  <span className="font-semibold text-white text-sm">{info.name}</span>
                </div>
                <p className="text-xs text-white/50">{info.description}</p>
                <Badge variant="neutral" className="mt-2 text-[9px]">{info.format}</Badge>
              </motion.div>
            ))}
          </div>
        </div>

        {/* AI Provider Configuration */}
        <div className="mb-6">
          <h3 className="text-lg font-semibold text-white mb-3 flex items-center gap-2">
            <Bot className="w-5 h-5 text-[#E95420]" /> AI Provider Configuration
          </h3>
          
          <div className="space-y-4">
            {/* Provider Selection */}
            <div>
              <label className="text-xs text-white/50 mb-2 block">AI Provider</label>
              <div className="grid grid-cols-3 gap-2">
                {Object.entries(aiProviders).map(([key, info]) => (
                  <button key={key} onClick={() => handleProviderChange(key)}
                    className={`p-3 rounded-lg text-left ${selectedProvider === key ? "bg-[#E95420]/20 border border-[#E95420]/50" : "bg-black/20 border border-white/5"}`}>
                    <div className="font-medium text-sm text-white">{info.name}</div>
                    {info.built_in && <Badge variant="success" className="mt-1 text-[9px]">Built-in</Badge>}
                    {info.local && <Badge variant="neutral" className="mt-1 text-[9px]">Local</Badge>}
                  </button>
                ))}
              </div>
            </div>

            {/* Model Selection */}
            {currentProvider.models && (
              <div>
                <label className="text-xs text-white/50 mb-2 block">Model</label>
                <select value={selectedModel} onChange={(e) => setSelectedModel(e.target.value)}
                  className="input-dark w-full">
                  {currentProvider.models.map(model => (
                    <option key={model} value={model}>{model}</option>
                  ))}
                </select>
              </div>
            )}

            {/* API Key (if needed) */}
            {currentProvider.requires_key && !currentProvider.built_in && (
              <div>
                <label className="text-xs text-white/50 mb-2 block flex items-center gap-2">
                  API Key <Lock className="w-3 h-3" />
                </label>
                <input type="password" value={apiKey} onChange={(e) => setApiKey(e.target.value)}
                  placeholder="Enter your API key" className="input-dark w-full" />
                <p className="text-xs text-white/40 mt-1">
                  Your key is only stored in the compiled app, never sent to our servers
                </p>
              </div>
            )}

            {selectedProvider === "emergent" && (
              <div className="p-3 bg-green-500/10 border border-green-500/30 rounded-lg">
                <p className="text-sm text-green-300 flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4" />
                  Using Emergent LLM - No API key needed! Works out of the box.
                </p>
              </div>
            )}

            {currentProvider.local && (
              <div className="p-3 bg-blue-500/10 border border-blue-500/30 rounded-lg">
                <p className="text-sm text-blue-300">
                  <Info className="w-4 h-4 inline mr-1" />
                  Local AI - Runs on your machine. Install {currentProvider.name} separately.
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Compile Button */}
        <button onClick={compileApp} disabled={compiling || (currentProvider.requires_key && !apiKey && !currentProvider.built_in)}
          className="w-full py-3 rounded-xl font-semibold flex items-center justify-center gap-2 bg-[#E95420] text-white hover:bg-[#E95420]/90 transition-all disabled:opacity-50 disabled:cursor-not-allowed">
          {compiling ? (
            <><Loader2 className="w-5 h-5 animate-spin" /> Compiling...</>
          ) : (
            <><Rocket className="w-5 h-5" /> Compile {currentPlatform.name}</>
          )}
        </button>

        {/* Result */}
        {result && (
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
            className="mt-6 p-4 bg-green-500/10 border border-green-500/30 rounded-xl">
            <div className="flex items-center gap-2 mb-3">
              <CheckCheck className="w-5 h-5 text-green-400" />
              <span className="font-semibold text-green-300">Compilation Successful!</span>
            </div>
            <p className="text-sm text-white/70 mb-3">{result.message}</p>
            <div className="flex gap-2">
              <a href={`${API}/compiler/downloads/${result.package_path?.split('/').pop()?.replace('.zip', '')}`}
                className="btn-primary flex items-center gap-2">
                <Download className="w-4 h-4" /> Download Package
              </a>
            </div>
            <p className="text-xs text-white/40 mt-3">
              Platform: {result.platform} • AI: {result.ai_provider}
            </p>
          </motion.div>
        )}

        {/* Info Box */}
        <div className="mt-6 p-4 bg-blue-500/10 border border-blue-500/30 rounded-xl">
          <p className="text-sm text-blue-300 mb-2">
            <Info className="w-4 h-4 inline mr-1" />
            <strong>What you'll get:</strong>
          </p>
          <ul className="text-xs text-white/60 space-y-1 ml-5">
            <li>• Standalone app with embedded backend + frontend</li>
            <li>• All features work offline (except AI API calls)</li>
            <li>• Binary auto-installer included</li>
            <li>• README with installation instructions</li>
            <li>• No web server needed - runs entirely on your machine</li>
          </ul>
        </div>
      </motion.div>
    </div>
  );
};

// ======================= BINARY MANAGER MODAL =======================

const BinaryManagerModal = ({ show, onClose }) => {
  const [binaries, setBinaries] = useState({});
  const [loading, setLoading] = useState(false);
  const [installing, setInstalling] = useState(null);

  useEffect(() => {
    if (show) {
      fetchBinaries();
    }
  }, [show]);

  const fetchBinaries = async () => {
    try {
      const res = await axios.get(`${API}/binaries/status`);
      setBinaries(res.data.binaries);
    } catch (e) {
      toast.error("Failed to fetch binary status");
    }
  };

  const installBinary = async (name) => {
    setInstalling(name);
    try {
      const res = await axios.post(`${API}/binaries/${name}/install`);
      toast.success(res.data.message);
      fetchBinaries();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Installation failed");
    } finally {
      setInstalling(null);
    }
  };

  if (!show) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm" onClick={onClose}>
      <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }}
        onClick={(e) => e.stopPropagation()}
        className="glass-card rounded-2xl p-6 max-w-3xl w-full mx-4 max-h-[80vh] overflow-y-auto">
        
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <Settings className="w-6 h-6 text-[#E95420]" />
            Binary Manager
          </h2>
          <button onClick={onClose} className="text-white/50 hover:text-white">
            <XCircle className="w-6 h-6" />
          </button>
        </div>

        <p className="text-sm text-white/60 mb-6">
          Required build tools and their status. Install missing binaries or configure custom paths.
        </p>

        <div className="space-y-3">
          {Object.entries(binaries).map(([name, info]) => (
            <div key={name} className="p-4 bg-black/30 rounded-xl border border-white/5 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                  info.available ? "bg-green-500/20" : "bg-red-500/20"
                }`}>
                  {info.available ? (
                    <CheckCircle2 className="w-5 h-5 text-green-400" />
                  ) : (
                    <XOctagon className="w-5 h-5 text-red-400" />
                  )}
                </div>
                <div>
                  <span className="font-mono text-white font-medium">{name}</span>
                  {info.path && (
                    <p className="text-xs text-white/40 font-mono">{info.path}</p>
                  )}
                </div>
              </div>

              <div className="flex items-center gap-2">
                {info.available ? (
                  <Badge variant="success">Installed</Badge>
                ) : info.can_auto_install ? (
                  <button 
                    onClick={() => installBinary(name)}
                    disabled={installing === name}
                    className="px-3 py-1.5 rounded-lg bg-[#E95420] text-white text-sm font-medium flex items-center gap-2 hover:bg-[#E95420]/90 disabled:opacity-50">
                    {installing === name ? (
                      <><Loader2 className="w-3 h-3 animate-spin" /> Installing...</>
                    ) : (
                      <><Download className="w-3 h-3" /> Install</>
                    )}
                  </button>
                ) : (
                  <Badge variant="error">Manual Install Required</Badge>
                )}
              </div>
            </div>
          ))}
        </div>

        <div className="mt-6 p-4 bg-blue-500/10 border border-blue-500/30 rounded-xl">
          <p className="text-sm text-blue-300">
            <Info className="w-4 h-4 inline mr-1" />
            Binaries are detected from system PATH or downloaded to /tmp/linux_forge/binaries/
          </p>
        </div>
      </motion.div>
    </div>
  );
};

// ======================= BUILD COMPLEXITY SELECTOR =======================

const BuildComplexitySelector = ({ selected, onSelect, toolType }) => {
  const complexities = {
    quick: {
      icon: Zap,
      name: "Quick Build",
      description: "One-click build with smart defaults",
      time: "5 min",
      difficulty: "Beginner",
      color: "green"
    },
    selective: {
      icon: Sliders,
      name: "Selective Build",
      description: "Choose specific options manually",
      time: "15-30 min",
      difficulty: "Intermediate",
      color: "blue"
    },
    ai_guided: {
      icon: Bot,
      name: "AI-Guided Build",
      description: "Describe what you want, AI configures it",
      time: "10 min",
      difficulty: "Any Level",
      color: "purple"
    }
  };

  return (
    <div className="grid grid-cols-3 gap-3 mb-4">
      {Object.entries(complexities).map(([key, info]) => {
        const Icon = info.icon;
        const isSelected = selected === key;
        return (
          <motion.button key={key} whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}
            onClick={() => onSelect(key)}
            className={`p-4 rounded-xl text-left transition-all ${
              isSelected 
                ? `bg-${info.color}-500/20 border-2 border-${info.color}-500/50` 
                : "glass-card hover:border-white/20"
            }`}>
            <div className="flex items-center gap-2 mb-2">
              <Icon className={`w-5 h-5 text-${info.color}-400`} />
              <span className="font-semibold text-white text-sm">{info.name}</span>
            </div>
            <p className="text-xs text-white/50 mb-2">{info.description}</p>
            <div className="flex items-center justify-between text-[10px]">
              <Badge variant={info.difficulty === "Beginner" ? "success" : info.difficulty === "Intermediate" ? "warning" : "primary"}>
                {info.difficulty}
              </Badge>
              <span className="text-white/40">{info.time}</span>
            </div>
          </motion.button>
        );
      })}
    </div>
  );
};

// ======================= AI ASSISTANT PANEL (Universal) =======================

const AIAssistantPanel = ({ toolType, deviceInfo, onConfigGenerated }) => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId] = useState(() => `ai-${toolType}-${Date.now()}`);

  const sendMessage = async () => {
    if (!input.trim()) return;
    
    const userMsg = { role: "user", content: input };
    setMessages(prev => [...prev, userMsg]);
    setInput("");
    setIsLoading(true);

    try {
      const res = await axios.post(`${API}/ai/build-assistant`, {
        session_id: sessionId,
        message: input,
        tool_type: toolType,
        context: { device_info: deviceInfo }
      });
      
      const aiMsg = { role: "assistant", content: res.data.response };
      setMessages(prev => [...prev, aiMsg]);
    } catch (e) {
      toast.error("AI assistant error");
    } finally {
      setIsLoading(false);
    }
  };

  const generateConfig = async () => {
    if (!input.trim()) {
      toast.error("Describe what you want to build");
      return;
    }

    setIsLoading(true);
    try {
      let res;
      if (toolType === "kernel") {
        res = await axios.post(`${API}/ai/generate-kernel-config`, {
          description: input,
          device_info: deviceInfo
        });
        onConfigGenerated(res.data.config);
        toast.success("Kernel config generated!");
      } else if (toolType === "os") {
        res = await axios.post(`${API}/ai/recommend-os`, {
          description: input,
          device_info: deviceInfo
        });
        onConfigGenerated(res.data.recommendation);
        toast.success("OS recommendation ready!");
      }
      
      const aiMsg = { 
        role: "assistant", 
        content: `✅ Generated configuration based on: "${input}"\n\nCheck the main panel for details!`
      };
      setMessages(prev => [...prev, { role: "user", content: input }, aiMsg]);
      setInput("");
    } catch (e) {
      toast.error("Failed to generate config");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="glass-card rounded-xl p-4">
      <div className="flex items-center gap-2 mb-3">
        <Bot className="w-5 h-5 text-purple-400" />
        <h3 className="font-semibold text-white">AI Assistant</h3>
        <Badge variant="primary" className="text-[9px]">Context-Aware</Badge>
      </div>

      {/* Chat Messages */}
      <div className="bg-black/30 rounded-lg p-3 mb-3 max-h-64 overflow-y-auto space-y-2">
        {messages.length === 0 ? (
          <div className="text-center text-white/40 text-sm py-4">
            <Bot className="w-8 h-8 mx-auto mb-2 opacity-50" />
            <p>Describe what you want to build in natural language</p>
            <p className="text-xs mt-1">Example: "I want maximum battery life and Docker support"</p>
          </div>
        ) : (
          messages.map((msg, i) => (
            <div key={i} className={`p-2 rounded ${msg.role === "user" ? "bg-blue-500/20 ml-8" : "bg-purple-500/20 mr-8"}`}>
              <span className="text-xs font-semibold text-white/70">{msg.role === "user" ? "You" : "AI"}</span>
              <p className="text-sm text-white whitespace-pre-wrap">{msg.content}</p>
            </div>
          ))
        )}
        {isLoading && (
          <div className="flex items-center gap-2 text-white/50">
            <Loader2 className="w-4 h-4 animate-spin" />
            <span className="text-sm">AI is thinking...</span>
          </div>
        )}
      </div>

      {/* Input */}
      <div className="space-y-2">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && e.ctrlKey) {
              sendMessage();
            }
          }}
          placeholder="Describe what you want... (Ctrl+Enter to send)"
          className="input-dark w-full text-sm resize-none"
          rows={2}
        />
        <div className="flex gap-2">
          <button onClick={sendMessage} disabled={isLoading || !input.trim()}
            className="btn-outline flex-1 text-sm">
            <MessageSquare className="w-4 h-4 mr-1" /> Chat
          </button>
          <button onClick={generateConfig} disabled={isLoading || !input.trim()}
            className="btn-primary flex-1 text-sm">
            <Sparkles className="w-4 h-4 mr-1" /> Generate Config
          </button>
        </div>
      </div>

      <p className="text-[10px] text-white/30 mt-2 text-center">
        AI understands {toolType} building and your device context
      </p>
    </div>
  );
};

// ======================= DEVICE PANEL =======================

const DevicePanel = ({ device, deviceInfo, onRefresh, onSelect }) => {
  const [loading, setLoading] = useState(false);

  const fetchInfo = async () => {
    if (!device?.serial) return;
    setLoading(true);
    try {
      const res = await axios.get(`${API}/devices/${device.serial}/info`);
      onSelect(device, res.data);
    } catch (e) {
      toast.error("Failed to fetch device info");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (device?.state === "device" && !deviceInfo) {
      fetchInfo();
    }
  }, [device]);

  if (!device) {
    return (
      <div className="glass-card rounded-xl p-6 flex flex-col items-center justify-center min-h-[200px]">
        <Smartphone className="w-12 h-12 text-white/20 mb-3" />
        <p className="text-white/40 text-sm">No device connected</p>
        <p className="text-white/30 text-xs mt-1">Connect via USB and enable ADB</p>
        <button onClick={onRefresh} className="btn-outline text-xs mt-4">
          <RefreshCw className="w-3.5 h-3.5 mr-1.5" /> Scan Devices
        </button>
      </div>
    );
  }

  return (
    <div className="glass-card rounded-xl p-5">
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${device.state === "device" ? "bg-green-500/20" : "bg-yellow-500/20"}`}>
            <Smartphone className={`w-5 h-5 ${device.state === "device" ? "text-green-400" : "text-yellow-400"}`} />
          </div>
          <div>
            <h3 className="font-semibold text-white">{deviceInfo?.model || device.serial}</h3>
            <p className="text-xs text-white/50">{device.serial}</p>
          </div>
        </div>
        <Badge variant={device.state === "device" ? "success" : "warning"}>{device.state}</Badge>
      </div>

      {loading ? (
        <div className="flex items-center gap-2 text-white/40"><Loader2 className="w-4 h-4 animate-spin" />Loading...</div>
      ) : deviceInfo ? (
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-2 text-sm">
            <div className="bg-black/20 rounded p-2">
              <span className="text-white/40 text-xs">Codename</span>
              <p className="text-white font-mono">{deviceInfo.codename || deviceInfo.device}</p>
            </div>
            <div className="bg-black/20 rounded p-2">
              <span className="text-white/40 text-xs">Architecture</span>
              <p className="text-white font-mono">{deviceInfo.architecture || deviceInfo.cpu_abi}</p>
            </div>
            <div className="bg-black/20 rounded p-2">
              <span className="text-white/40 text-xs">Android</span>
              <p className="text-white">{deviceInfo.android_version}</p>
            </div>
            <div className="bg-black/20 rounded p-2">
              <span className="text-white/40 text-xs">SoC</span>
              <p className="text-white text-xs">{deviceInfo.soc || deviceInfo.platform}</p>
            </div>
          </div>
          <div className="flex gap-2 mt-3">
            <button onClick={fetchInfo} className="btn-outline text-xs py-1.5 flex-1"><RefreshCw className="w-3 h-3 mr-1" /> Refresh</button>
            <button onClick={onRefresh} className="btn-outline text-xs py-1.5 flex-1"><HardDrive className="w-3 h-3 mr-1" /> Scan All</button>
          </div>
        </div>
      ) : null}
    </div>
  );
};

// ======================= KERNEL FORGE PANEL =======================

const KernelForgePanel = ({ deviceInfo, sessionId }) => {
  const [projects, setProjects] = useState([]);
  const [selectedProject, setSelectedProject] = useState(null);
  const [configAnalysis, setConfigAnalysis] = useState(null);
  const [kernelSource, setKernelSource] = useState("");
  const [loading, setLoading] = useState(false);
  const [mainlineVersions, setMainlineVersions] = useState({});

  useEffect(() => {
    fetchProjects();
    fetchMainlineVersions();
  }, []);

  const fetchProjects = async () => {
    try {
      const res = await axios.get(`${API}/kernel/projects`);
      setProjects(res.data.projects);
    } catch (e) {}
  };

  const fetchMainlineVersions = async () => {
    try {
      const res = await axios.get(`${API}/kernel/mainline-versions`);
      setMainlineVersions(res.data.versions);
    } catch (e) {}
  };

  const createProject = async () => {
    if (!deviceInfo?.codename && !deviceInfo?.device) {
      toast.error("Please connect a device first");
      return;
    }
    setLoading(true);
    try {
      const res = await axios.post(`${API}/kernel/projects`, {
        device_codename: deviceInfo.codename || deviceInfo.device,
        architecture: deviceInfo.architecture || "arm64",
        kernel_source: kernelSource || null
      });
      setProjects([res.data, ...projects]);
      setSelectedProject(res.data);
      toast.success("Kernel project created");
    } catch (e) {
      toast.error("Failed to create project");
    } finally {
      setLoading(false);
    }
  };

  const analyzeConfig = async () => {
    if (!selectedProject) return;
    setLoading(true);
    try {
      const res = await axios.post(`${API}/kernel/projects/${selectedProject.id}/analyze`);
      setConfigAnalysis(res.data);
    } catch (e) {
      toast.error("Failed to analyze config");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="glass-card rounded-xl p-5">
        <h3 className="font-semibold text-white flex items-center gap-2 mb-4">
          <FolderGit2 className="w-4 h-4 text-[#E95420]" /> Kernel Project
        </h3>
        <div className="space-y-3">
          <input type="text" placeholder="Kernel source URL (git)" value={kernelSource}
            onChange={(e) => setKernelSource(e.target.value)} className="input-dark w-full text-sm" />
          <button onClick={createProject} disabled={loading || (!deviceInfo?.codename && !deviceInfo?.device)}
            className="btn-primary w-full flex items-center justify-center gap-2">
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <GitBranch className="w-4 h-4" />}
            Create Kernel Project
          </button>
        </div>
        {projects.length > 0 && (
          <div className="mt-4">
            <label className="text-xs text-white/50 mb-2 block">Existing Projects</label>
            <div className="space-y-2 max-h-32 overflow-y-auto">
              {projects.map((p) => (
                <div key={p.id} onClick={() => setSelectedProject(p)}
                  className={`p-2 rounded cursor-pointer ${selectedProject?.id === p.id ? "bg-[#E95420]/20 border border-[#E95420]/30" : "bg-black/20"}`}>
                  <span className="text-sm text-white">{p.name}</span>
                  <Badge variant="neutral" className="ml-2 text-[9px]">{p.build_status}</Badge>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {selectedProject && (
        <div className="glass-card rounded-xl p-5">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-white flex items-center gap-2">
              <Cog className="w-4 h-4 text-[#E95420]" /> Config Analysis
            </h3>
            <button onClick={analyzeConfig} className="btn-outline text-xs">
              {loading ? <Loader2 className="w-3 h-3 animate-spin" /> : "Analyze"}
            </button>
          </div>
          {configAnalysis && (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-white/60 text-sm">Score</span>
                <div className="flex items-center gap-2">
                  <div className="w-24 h-2 bg-black/30 rounded-full overflow-hidden">
                    <div className={`h-full ${configAnalysis.compatibility_score >= 80 ? "bg-green-500" : "bg-yellow-500"}`}
                      style={{ width: `${configAnalysis.compatibility_score}%` }} />
                  </div>
                  <span className="text-white font-mono text-sm">{configAnalysis.compatibility_score}%</span>
                </div>
              </div>
              <Badge variant={configAnalysis.linux_ready ? "success" : "error"}>
                {configAnalysis.linux_ready ? "Linux Ready" : "Needs Fixes"}
              </Badge>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

// ======================= OS IMAGE BUILDER PANEL =======================

const OSImageBuilderPanel = ({ deviceInfo }) => {
  const [distros, setDistros] = useState({ mobile: {}, desktop: {} });
  const [selectedDistro, setSelectedDistro] = useState(null);
  const [distroType, setDistroType] = useState("mobile");
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchDistros();
    fetchProjects();
  }, []);

  const fetchDistros = async () => {
    try {
      const res = await axios.get(`${API}/os/distros`);
      setDistros(res.data);
    } catch (e) {}
  };

  const fetchProjects = async () => {
    try {
      const res = await axios.get(`${API}/os/projects`);
      setProjects(res.data.projects);
    } catch (e) {}
  };

  const createProject = async () => {
    if (!selectedDistro || !deviceInfo?.codename) {
      toast.error("Select a distro and connect a device");
      return;
    }
    setLoading(true);
    try {
      const res = await axios.post(`${API}/os/projects`, {
        device_codename: deviceInfo.codename || deviceInfo.device,
        distro: selectedDistro,
      });
      setProjects([res.data, ...projects]);
      toast.success("OS project created");
    } catch (e) {
      toast.error("Failed to create project");
    } finally {
      setLoading(false);
    }
  };

  const currentDistros = distroType === "mobile" ? distros.mobile : distros.desktop;

  return (
    <div className="space-y-4">
      <div className="glass-card rounded-xl p-5">
        <h3 className="font-semibold text-white flex items-center gap-2 mb-4">
          <Package className="w-4 h-4 text-[#E95420]" /> Select Distribution
        </h3>
        <div className="flex gap-2 mb-4">
          <button onClick={() => setDistroType("mobile")}
            className={`flex-1 py-2 rounded-lg text-sm font-medium ${distroType === "mobile" ? "bg-purple-500/20 text-purple-400 border border-purple-500/30" : "bg-black/20 text-white/60"}`}>
            <Smartphone className="w-4 h-4 inline mr-2" />Mobile ({Object.keys(distros.mobile || {}).length})
          </button>
          <button onClick={() => setDistroType("desktop")}
            className={`flex-1 py-2 rounded-lg text-sm font-medium ${distroType === "desktop" ? "bg-blue-500/20 text-blue-400 border border-blue-500/30" : "bg-black/20 text-white/60"}`}>
            <Monitor className="w-4 h-4 inline mr-2" />Desktop ({Object.keys(distros.desktop || {}).length})
          </button>
        </div>
        <div className="grid grid-cols-2 gap-3 max-h-64 overflow-y-auto">
          {Object.entries(currentDistros).map(([key, info]) => (
            <DistroCard key={key} distro={key} info={info} selected={selectedDistro === key} onSelect={setSelectedDistro} />
          ))}
        </div>
        <button onClick={createProject} disabled={!selectedDistro || !deviceInfo || loading}
          className="btn-primary w-full mt-4">
          {loading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Box className="w-4 h-4 mr-2" />}
          Create OS Image Project
        </button>
      </div>

      <div className="glass-card rounded-xl p-5">
        <h3 className="font-semibold text-white flex items-center gap-2 mb-4">
          <Upload className="w-4 h-4 text-[#E95420]" /> Custom Rootfs Upload
        </h3>
        <label className="block">
          <div className="border-2 border-dashed border-white/10 rounded-lg p-6 text-center cursor-pointer hover:border-white/20">
            <Upload className="w-8 h-8 text-white/30 mx-auto mb-2" />
            <span className="text-sm text-white/40">Click to upload (.tar.gz, .tar.xz, .zip)</span>
          </div>
          <input type="file" className="hidden" accept=".tar.gz,.tar.xz,.zip" />
        </label>
      </div>
    </div>
  );
};

// ======================= ANDROID BUILDER PANEL =======================

const AndroidBuilderPanel = ({ deviceInfo, sessionId }) => {
  const [interviewDepths, setInterviewDepths] = useState({});
  const [selectedDepth, setSelectedDepth] = useState("standard");
  const [project, setProject] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [romBases, setRomBases] = useState({});
  const chatRef = useRef(null);

  useEffect(() => {
    fetchInterviewDepths();
    fetchRomBases();
  }, []);

  useEffect(() => {
    if (chatRef.current) {
      chatRef.current.scrollTop = chatRef.current.scrollHeight;
    }
  }, [messages]);

  const fetchInterviewDepths = async () => {
    try {
      const res = await axios.get(`${API}/android/interview-depths`);
      setInterviewDepths(res.data.depths);
    } catch (e) {}
  };

  const fetchRomBases = async () => {
    try {
      const res = await axios.get(`${API}/android/rom-bases`);
      setRomBases(res.data.rom_bases);
    } catch (e) {}
  };

  const startInterview = async () => {
    if (!deviceInfo?.codename && !deviceInfo?.device) {
      toast.error("Please connect a device first");
      return;
    }
    setLoading(true);
    try {
      const res = await axios.post(`${API}/android/projects`, {
        device_codename: deviceInfo.codename || deviceInfo.device,
        device_serial: deviceInfo.serial,
        interview_depth: selectedDepth
      });
      setProject(res.data.project);
      setMessages([{ role: "assistant", content: res.data.first_message, timestamp: new Date().toISOString() }]);
      toast.success("Interview started!");
    } catch (e) {
      toast.error("Failed to start interview");
    } finally {
      setLoading(false);
    }
  };

  const sendMessage = async () => {
    if (!input.trim() || !project || loading) return;
    
    const userMsg = { role: "user", content: input, timestamp: new Date().toISOString() };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const res = await axios.post(`${API}/android/projects/${project.id}/interview`, {
        project_id: project.id,
        message: input
      });
      
      setMessages((prev) => [...prev, {
        role: "assistant",
        content: res.data.response,
        timestamp: new Date().toISOString()
      }]);

      if (res.data.interview_complete) {
        setProject((prev) => ({ ...prev, interview_complete: true, build_status: "ready" }));
        toast.success("Interview complete! Ready to build.");
      }
    } catch (e) {
      toast.error("Failed to send message");
    } finally {
      setLoading(false);
    }
  };

  const startBuild = async () => {
    if (!project) return;
    try {
      await axios.post(`${API}/android/projects/${project.id}/build`);
      toast.success("Android build started!");
    } catch (e) {
      toast.error("Failed to start build");
    }
  };

  const formatMessage = (content) => {
    // Simple formatting for numbered options
    return content.split('\n').map((line, i) => {
      if (/^\d+\./.test(line.trim())) {
        return <div key={i} className="ml-4 my-1 text-white/80">{line}</div>;
      }
      if (line.startsWith('**') && line.endsWith('**')) {
        return <div key={i} className="font-semibold text-white mt-2">{line.replace(/\*\*/g, '')}</div>;
      }
      return <div key={i}>{line}</div>;
    });
  };

  // Pre-interview: Show depth selection
  if (!project) {
    return (
      <div className="space-y-4" data-testid="android-builder-panel">
        <div className="glass-card rounded-xl p-5">
          <h3 className="font-semibold text-white flex items-center gap-2 mb-4">
            <MessageSquare className="w-4 h-4 text-[#3DDC84]" />
            Build Interview Depth
          </h3>
          <p className="text-sm text-white/60 mb-4">
            Choose how detailed you want the configuration process to be. The AI will ask questions to understand exactly what you want from your custom Android ROM.
          </p>
          <div className="grid grid-cols-1 gap-3">
            {Object.entries(interviewDepths).map(([key, info]) => (
              <InterviewDepthCard key={key} depth={key} info={info} selected={selectedDepth === key} onSelect={setSelectedDepth} />
            ))}
          </div>
          <button onClick={startInterview} disabled={loading || !deviceInfo}
            className="w-full mt-4 py-3 rounded-xl font-semibold flex items-center justify-center gap-2 bg-[#3DDC84] text-black hover:bg-[#3DDC84]/90 transition-all"
            data-testid="start-interview-btn">
            {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Sparkles className="w-5 h-5" />}
            Start Building Your ROM
          </button>
        </div>

        <div className="glass-card rounded-xl p-5">
          <h3 className="font-semibold text-white flex items-center gap-2 mb-4">
            <Database className="w-4 h-4 text-[#3DDC84]" />
            Available ROM Bases
          </h3>
          <div className="grid grid-cols-2 gap-2 max-h-48 overflow-y-auto">
            {Object.entries(romBases).map(([key, info]) => (
              <div key={key} className="p-2 bg-black/20 rounded-lg">
                <span className="text-white text-sm font-medium">{info.name}</span>
                <p className="text-xs text-white/40 line-clamp-1">{info.description}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  // Active interview: Show chat interface
  return (
    <div className="flex flex-col h-full" data-testid="android-builder-panel">
      <div className="glass-card rounded-xl flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        <div className="px-4 py-3 border-b border-white/5 bg-[#3DDC84]/10 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Bot className="w-5 h-5 text-[#3DDC84]" />
            <span className="font-semibold text-white">ROM Builder AI</span>
            <Badge variant="android">{selectedDepth}</Badge>
          </div>
          {project.interview_complete && (
            <button onClick={startBuild} className="px-4 py-1.5 rounded-lg bg-[#3DDC84] text-black text-sm font-medium flex items-center gap-2">
              <Rocket className="w-4 h-4" /> Build ROM
            </button>
          )}
        </div>

        {/* Chat Messages */}
        <div ref={chatRef} className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.map((msg, i) => (
            <motion.div key={i} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
              className={msg.role === "user" ? "ml-12" : "mr-12"}>
              <div className={`rounded-xl p-4 ${
                msg.role === "user"
                  ? "bg-[#3DDC84]/20 border border-[#3DDC84]/30"
                  : "bg-black/30 border border-white/5"
              }`}>
                <div className="flex items-center gap-2 mb-2">
                  {msg.role === "assistant" ? (
                    <Bot className="w-4 h-4 text-[#3DDC84]" />
                  ) : (
                    <span className="text-[#3DDC84] text-xs font-mono">you</span>
                  )}
                  <span className="text-xs text-white/30">{new Date(msg.timestamp).toLocaleTimeString()}</span>
                </div>
                <div className="text-sm text-white/80 whitespace-pre-wrap">
                  {formatMessage(msg.content)}
                </div>
              </div>
            </motion.div>
          ))}
          {loading && (
            <div className="flex items-center gap-2 text-white/40 p-4">
              <Loader2 className="w-4 h-4 animate-spin" />
              <span className="text-sm">AI is thinking...</span>
            </div>
          )}
        </div>

        {/* Input */}
        <div className="p-4 border-t border-white/5 bg-black/20">
          <div className="flex gap-2">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && sendMessage()}
              placeholder={project.interview_complete ? "Interview complete!" : "Type your answer..."}
              className="input-dark flex-1"
              disabled={loading || project.interview_complete}
              data-testid="android-chat-input"
            />
            <button onClick={sendMessage} disabled={loading || !input.trim() || project.interview_complete}
              className="px-4 py-2 rounded-lg bg-[#3DDC84] text-black font-medium disabled:opacity-50"
              data-testid="android-chat-submit">
              <Send className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

// ======================= RECOVERY BUILDER PANEL =======================

const RecoveryBuilderPanel = ({ deviceInfo }) => {
  const [recoveries, setRecoveries] = useState({});
  const [selectedRecovery, setSelectedRecovery] = useState("twrp");
  const [builds, setBuilds] = useState([]);
  const [loading, setLoading] = useState(false);
  const [rootSolution, setRootSolution] = useState("none");
  const [rootSolutions, setRootSolutions] = useState({});
  const [organizedRoots, setOrganizedRoots] = useState({});
  const [hidingModules, setHidingModules] = useState({});
  const [selectedHiding, setSelectedHiding] = useState([]);
  const [patchMethod, setPatchMethod] = useState("kprobe");
  const [patchMethods, setPatchMethods] = useState({});
  const [showAdvanced, setShowAdvanced] = useState(false);

  useEffect(() => {
    fetchRecoveryTypes();
    fetchRootSolutions();
    fetchBuilds();
  }, []);

  const fetchRecoveryTypes = async () => {
    try {
      const res = await axios.get(`${API}/recovery/types`);
      setRecoveries(res.data.recoveries);
    } catch (e) {}
  };

  const fetchRootSolutions = async () => {
    try {
      const res = await axios.get(`${API}/root/solutions`);
      setRootSolutions(res.data.solutions);
      setOrganizedRoots(res.data.organized);
      setHidingModules(res.data.hiding_modules);
      setPatchMethods(res.data.patch_methods);
    } catch (e) {}
  };

  const fetchBuilds = async () => {
    try {
      const res = await axios.get(`${API}/recovery/builds`);
      setBuilds(res.data.builds || []);
    } catch (e) {}
  };

  const startBuild = async () => {
    if (!deviceInfo?.codename && !deviceInfo?.device) {
      toast.error("Connect a device first");
      return;
    }
    setLoading(true);
    try {
      await axios.post(`${API}/recovery/build`, { 
        device_codename: deviceInfo.codename || deviceInfo.device, 
        recovery_type: selectedRecovery 
      });
      toast.success(`${recoveries[selectedRecovery]?.full_name} build started!`);
      fetchBuilds();
    } catch (e) {
      toast.error("Failed to start build");
    } finally {
      setLoading(false);
    }
  };

  const currentRoot = rootSolutions[rootSolution] || {};
  const requiresKernelPatch = currentRoot.kernel_patch;
  const currentMethod = patchMethods[patchMethod] || {};

  const toggleHiding = (module) => {
    setSelectedHiding(prev => 
      prev.includes(module) ? prev.filter(m => m !== module) : [...prev, module]
    );
  };

  return (
    <div className="space-y-4" data-testid="recovery-builder-panel">
      <div className="glass-card rounded-xl p-5">
        <h3 className="font-semibold text-white flex items-center gap-2 mb-4">
          <Wrench className="w-4 h-4 text-[#E95420]" /> Select Recovery
        </h3>
        <div className="grid grid-cols-2 gap-3">
          {Object.entries(recoveries).map(([key, info]) => (
            <motion.div key={key} whileHover={{ scale: 1.02 }}
              onClick={() => setSelectedRecovery(key)}
              className={`p-4 rounded-xl cursor-pointer transition-all ${
                selectedRecovery === key ? "bg-[#E95420]/20 border-2 border-[#E95420]/50" : "glass-card hover:border-white/20"
              }`}>
              <div className="flex items-center gap-3 mb-2">
                <div className="w-10 h-10 rounded-lg bg-[#E95420]/20 flex items-center justify-center">
                  <Wrench className="w-5 h-5 text-[#E95420]" />
                </div>
                <div>
                  <h4 className="font-semibold text-white text-sm">{info.full_name}</h4>
                  <Badge variant="primary" className="text-[9px]">{info.name}</Badge>
                </div>
              </div>
              <p className="text-xs text-white/50 line-clamp-2">{info.description}</p>
            </motion.div>
          ))}
        </div>
      </div>

      <div className="glass-card rounded-xl p-5">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-semibold text-white flex items-center gap-2">
            <Shield className="w-4 h-4 text-[#E95420]" /> Root Integration
          </h3>
          <button onClick={() => setShowAdvanced(!showAdvanced)} className="text-xs text-[#E95420]">
            {showAdvanced ? "Hide" : "Show"} Advanced Options
          </button>
        </div>
        
        <div className="space-y-4">
          {/* Root Solution Selection by Category */}
          {Object.entries(organizedRoots).map(([category, solutions]) => {
            if (Object.keys(solutions).length === 0 || category === 'none') return null;
            return (
              <div key={category}>
                <label className="text-xs font-semibold text-white/70 mb-2 block uppercase">{category}</label>
                <div className="grid grid-cols-2 gap-2">
                  {Object.entries(solutions).map(([key, info]) => (
                    <button key={key} onClick={() => setRootSolution(key)}
                      className={`p-2 rounded-lg text-left text-xs ${rootSolution === key ? "bg-[#E95420]/20 border border-[#E95420]/50" : "bg-black/20 border border-white/5"}`}>
                      <div className="font-medium text-white">{info.name}</div>
                      {info.difficulty && <Badge variant={info.difficulty === 'easy' ? 'success' : info.difficulty === 'medium' ? 'warning' : 'error'} className="text-[8px] mt-1">{info.difficulty}</Badge>}
                    </button>
                  ))}
                </div>
              </div>
            );
          })}

          {/* Advanced Options */}
          {showAdvanced && rootSolution !== "none" && (
            <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }} className="space-y-4">
              
              {/* Kernel Patch Method (for kernel-based root) */}
              {requiresKernelPatch && (
                <div>
                  <label className="text-xs text-white/50 mb-2 block">Kernel Patch Method</label>
                  <select value={patchMethod} onChange={(e) => setPatchMethod(e.target.value)}
                    className="input-dark w-full text-xs">
                    {Object.entries(patchMethods).map(([key, method]) => (
                      <option key={key} value={key}>{method.name} - {method.difficulty}</option>
                    ))}
                  </select>
                  {currentMethod.description && (
                    <p className="text-[10px] text-white/40 mt-1">{currentMethod.description}</p>
                  )}
                </div>
              )}

              {/* Hiding/Spoofing Modules */}
              {rootSolution !== "none" && Object.keys(hidingModules).length > 0 && (
                <div>
                  <label className="text-xs text-white/50 mb-2 block">Hiding/Spoofing Modules (Optional)</label>
                  <div className="space-y-2">
                    {Object.entries(hidingModules).map(([key, module]) => {
                      const isCompatible = module.compatible_with.includes(rootSolution);
                      const isSelected = selectedHiding.includes(key);
                      
                      if (!isCompatible) return null;
                      
                      return (
                        <div key={key} 
                          onClick={() => isCompatible && toggleHiding(key)}
                          className={`p-3 rounded-lg cursor-pointer transition-all ${
                            isSelected ? "bg-green-500/20 border border-green-500/50" : "bg-black/20 border border-white/5"
                          } ${!isCompatible && "opacity-50 cursor-not-allowed"}`}>
                          <div className="flex items-center justify-between mb-1">
                            <span className="text-xs font-semibold text-white">{module.name}</span>
                            <div className="flex items-center gap-2">
                              {module.kernel_patch_required && <Badge variant="warning" className="text-[8px]">Kernel Patch</Badge>}
                              <Badge variant={module.effectiveness === 'Very High' ? 'success' : 'neutral'} className="text-[8px]">{module.effectiveness}</Badge>
                            </div>
                          </div>
                          <p className="text-[10px] text-white/40">{module.description}</p>
                          {module.features && (
                            <div className="mt-2 flex flex-wrap gap-1">
                              {module.features.slice(0, 3).map((feat, i) => (
                                <span key={i} className="text-[9px] bg-white/5 px-2 py-0.5 rounded">{feat}</span>
                              ))}
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Info about selected root */}
              {currentRoot.safetynet && (
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div className="p-2 bg-black/20 rounded">
                    <span className="text-white/40">SafetyNet:</span>
                    <p className="text-white font-medium">{currentRoot.safetynet}</p>
                  </div>
                  <div className="p-2 bg-black/20 rounded">
                    <span className="text-white/40">Play Integrity:</span>
                    <p className="text-white font-medium">{currentRoot.play_integrity}</p>
                  </div>
                </div>
              )}

              {currentRoot.recommended_for && (
                <div className="p-3 bg-blue-500/10 border border-blue-500/30 rounded-lg">
                  <p className="text-xs text-blue-300">
                    <Info className="w-3 h-3 inline mr-1" />
                    Recommended for: {currentRoot.recommended_for}
                  </p>
                </div>
              )}

            </motion.div>
          )}

          {rootSolution !== "none" && !showAdvanced && currentRoot.description && (
            <p className="text-xs text-white/60">{currentRoot.description}</p>
          )}
        </div>
      </div>

      <div className="glass-card rounded-xl p-5">
        <button onClick={startBuild} disabled={!deviceInfo || loading} className="btn-primary w-full flex items-center justify-center gap-2">
          {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Rocket className="w-5 h-5" />}
          Build {recoveries[selectedRecovery]?.name || "Recovery"}
          {rootSolution !== "none" && ` + ${rootSolutions[rootSolution]?.name}`}
        </button>
        {selectedHiding.length > 0 && (
          <p className="text-[10px] text-white/40 mt-2 text-center">
            With {selectedHiding.length} hiding module{selectedHiding.length > 1 ? 's' : ''}
          </p>
        )}
      </div>

      {builds.length > 0 && (
        <div className="glass-card rounded-xl p-5">
          <h3 className="font-semibold text-white flex items-center gap-2 mb-4">
            <ScrollText className="w-4 h-4 text-[#E95420]" /> Recent Builds
          </h3>
          <div className="space-y-2 max-h-48 overflow-y-auto">
            {builds.slice(0, 5).map((build) => (
              <div key={build.id} className="p-3 bg-black/20 rounded-lg flex items-center justify-between">
                <div>
                  <span className="text-sm text-white font-medium">{build.recovery_type.toUpperCase()}</span>
                  <p className="text-xs text-white/40">{build.device_codename}</p>
                </div>
                <Badge variant={build.status === "completed" ? "success" : build.status === "building" ? "warning" : "error"}>
                  {build.status}
                </Badge>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

// ======================= HALIUM BUILDER PANEL =======================

const HaliumBuilderPanel = ({ deviceInfo }) => {
  const [haliumVersions, setHaliumVersions] = useState([]);
  const [selectedVersion, setSelectedVersion] = useState("halium-11.0");
  const [builds, setBuilds] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchVersions();
    fetchBuilds();
  }, []);

  const fetchVersions = async () => {
    try {
      const res = await axios.get(`${API}/halium/versions`);
      setHaliumVersions(res.data.versions);
    } catch (e) {}
  };

  const fetchBuilds = async () => {
    try {
      const res = await axios.get(`${API}/halium/builds`);
      setBuilds(res.data.builds || []);
    } catch (e) {}
  };

  const startBuild = async () => {
    if (!deviceInfo?.serial) {
      toast.error("Connect a device first");
      return;
    }
    setLoading(true);
    try {
      await axios.post(`${API}/halium/build`, { device_serial: deviceInfo.serial, halium_version: selectedVersion });
      toast.success("Halium build started");
      fetchBuilds();
    } catch (e) {
      toast.error("Failed to start build");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="glass-card rounded-xl p-5">
        <h3 className="font-semibold text-white flex items-center gap-2 mb-4">
          <Layers className="w-4 h-4 text-[#E95420]" /> Halium Version
        </h3>
        <div className="grid grid-cols-2 gap-2">
          {haliumVersions.map((v) => (
            <button key={v.id} onClick={() => setSelectedVersion(v.id)}
              className={`p-3 rounded-lg text-left ${selectedVersion === v.id ? "bg-[#E95420]/20 border border-[#E95420]/50" : "bg-black/20 border border-white/5"}`}>
              <div className="font-medium text-sm text-white">{v.name}</div>
              <div className="text-xs text-white/40">{v.android_base}</div>
              <Badge variant={v.status === "latest" ? "success" : "neutral"} className="mt-1 text-[9px]">{v.status}</Badge>
            </button>
          ))}
        </div>
      </div>
      <div className="glass-card rounded-xl p-5">
        <button onClick={startBuild} disabled={!deviceInfo || loading} className="btn-primary w-full">
          {loading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Zap className="w-4 h-4 mr-2" />}
          Start Halium Build
        </button>
      </div>
    </div>
  );
};

// ======================= TERMINAL & AI CHAT =======================

const Terminal = ({ history, onCommand, isLoading }) => {
  const [input, setInput] = useState("");
  const terminalRef = useRef(null);

  useEffect(() => {
    if (terminalRef.current) terminalRef.current.scrollTop = terminalRef.current.scrollHeight;
  }, [history]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (input.trim() && !isLoading) { onCommand(input.trim()); setInput(""); }
  };

  return (
    <div className="flex flex-col h-full bg-[#0A0A0A] rounded-lg overflow-hidden">
      <div className="flex items-center justify-between px-4 py-2 bg-black/50 border-b border-white/5">
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-[#C7162B]" />
          <div className="w-3 h-3 rounded-full bg-[#F99B11]" />
          <div className="w-3 h-3 rounded-full bg-[#0E8420]" />
        </div>
        <span className="text-xs text-white/40 font-mono">linux-forge</span>
      </div>
      <div ref={terminalRef} className="flex-1 overflow-y-auto p-4 font-mono text-sm space-y-2">
        {history.map((entry, i) => (
          <div key={i}>
            {entry.type === "command" && <div className="flex gap-2"><span className="terminal-prompt">❯</span><span className="terminal-command">{entry.content}</span></div>}
            {entry.type === "output" && <pre className="terminal-output whitespace-pre-wrap pl-4">{entry.content}</pre>}
            {entry.type === "error" && <pre className="terminal-error whitespace-pre-wrap pl-4">{entry.content}</pre>}
          </div>
        ))}
        {isLoading && <div className="flex items-center gap-2 text-white/40"><Loader2 className="w-4 h-4 animate-spin" />Executing...</div>}
      </div>
      <form onSubmit={handleSubmit} className="p-3 border-t border-white/5 bg-black/30">
        <div className="flex items-center gap-2">
          <span className="terminal-prompt">❯</span>
          <input type="text" value={input} onChange={(e) => setInput(e.target.value)} placeholder="Enter command..."
            className="flex-1 bg-transparent outline-none text-[#38D878] font-mono placeholder:text-white/20" disabled={isLoading} />
          <button type="submit" disabled={isLoading || !input.trim()} className="p-2 rounded hover:bg-white/5 text-white/40 disabled:opacity-30">
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
    if (chatRef.current) chatRef.current.scrollTop = chatRef.current.scrollHeight;
  }, [messages]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (input.trim() && !isLoading) { onSend(input.trim(), autoExecute); setInput(""); }
  };

  return (
    <div className="flex flex-col h-full">
      <div className="px-4 py-3 border-b border-white/5 bg-[#2C001E]/30 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Bot className="w-5 h-5 text-[#E95420]" />
          <span className="font-semibold text-white">AI Engineer</span>
          <Badge variant="neutral">Claude 4.5</Badge>
        </div>
        <label className="flex items-center gap-2 text-xs cursor-pointer">
          <input type="checkbox" checked={autoExecute} onChange={(e) => setAutoExecute(e.target.checked)} className="accent-[#E95420]" />
          <span className="text-white/50">Auto-execute</span>
        </label>
      </div>
      <div ref={chatRef} className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="text-center py-8">
            <Bot className="w-12 h-12 text-white/20 mx-auto mb-3" />
            <p className="text-white/40 text-sm">Ask about kernel, OS building, or device porting</p>
          </div>
        )}
        {messages.map((msg, i) => (
          <motion.div key={i} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className={msg.role === "user" ? "ml-8" : "mr-8"}>
            <div className={`rounded-xl p-4 ${msg.role === "user" ? "bg-[#E95420]/20 border border-[#E95420]/30" : "bg-black/30 border border-white/5"}`}>
              <div className="text-sm text-white/80 whitespace-pre-wrap">{msg.content}</div>
            </div>
          </motion.div>
        ))}
        {isLoading && <div className="flex items-center gap-2 text-white/40 p-4"><Loader2 className="w-4 h-4 animate-spin" /><span>AI is thinking...</span></div>}
      </div>
      <form onSubmit={handleSubmit} className="p-4 border-t border-white/5 bg-black/20">
        <div className="flex gap-2">
          <input type="text" value={input} onChange={(e) => setInput(e.target.value)} placeholder="Ask about kernel, OS, or porting..."
            className="input-dark flex-1" disabled={isLoading} />
          <button type="submit" disabled={isLoading || !input.trim()} className="btn-primary flex items-center gap-2">
            <Send className="w-4 h-4" />
          </button>
        </div>
      </form>
    </div>
  );
};

// ======================= MAIN DASHBOARD =======================

const Dashboard = () => {
  const [activeTool, setActiveTool] = useState("kernel");
  const [devices, setDevices] = useState([]);
  const [selectedDevice, setSelectedDevice] = useState(null);
  const [deviceInfo, setDeviceInfo] = useState(null);
  const [terminalHistory, setTerminalHistory] = useState([]);
  const [chatMessages, setChatMessages] = useState([]);
  const [isTerminalLoading, setIsTerminalLoading] = useState(false);
  const [isAiLoading, setIsAiLoading] = useState(false);
  const [bottomPanel, setBottomPanel] = useState("terminal");
  const [sessionId] = useState(() => `session-${Date.now()}`);
  const [showBinaryManager, setShowBinaryManager] = useState(false);
  const [showAppCompiler, setShowAppCompiler] = useState(false);

  useEffect(() => {
    fetchDevices();
    checkHealth();
  }, []);

  const checkHealth = async () => {
    try {
      const res = await axios.get(`${API}/health`);
      if (res.data.kernel_forge_ready) {
        addTerminalEntry("output", "Linux Device Forge v3.0 ready. All tools available.");
      }
    } catch (e) {
      addTerminalEntry("error", "Failed to connect to backend");
    }
  };

  const fetchDevices = async () => {
    try {
      const res = await axios.get(`${API}/devices`);
      setDevices(res.data.devices);
    } catch (e) {}
  };

  const handleDeviceSelect = (device, info) => {
    setSelectedDevice(device);
    setDeviceInfo(info);
  };

  const addTerminalEntry = (type, content) => {
    setTerminalHistory((prev) => [...prev, { type, content }]);
  };

  const handleTerminalCommand = async (command) => {
    setIsTerminalLoading(true);
    addTerminalEntry("command", command);
    try {
      const res = await axios.post(`${API}/terminal/execute`, { command, session_id: sessionId });
      if (res.data.stdout) addTerminalEntry("output", res.data.stdout);
      if (res.data.stderr) addTerminalEntry("error", res.data.stderr);
    } catch (e) {
      addTerminalEntry("error", e.message);
    } finally {
      setIsTerminalLoading(false);
    }
  };

  const handleAiChat = async (message, autoExecute) => {
    setIsAiLoading(true);
    setChatMessages((prev) => [...prev, { role: "user", content: message, timestamp: new Date().toISOString() }]);
    try {
      const res = await axios.post(`${API}/ai/chat`, { message, session_id: sessionId, device_context: deviceInfo, auto_execute: autoExecute });
      setChatMessages((prev) => [...prev, { role: "assistant", content: res.data.response, timestamp: new Date().toISOString() }]);
      if (autoExecute && res.data.extracted_commands?.length > 0) {
        for (const cmd of res.data.extracted_commands) await handleTerminalCommand(cmd);
      }
    } catch (e) {
      toast.error("AI chat failed");
    } finally {
      setIsAiLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col" data-testid="dashboard">
      <BinaryManagerModal show={showBinaryManager} onClose={() => setShowBinaryManager(false)} />
      <AppCompilerModal show={showAppCompiler} onClose={() => setShowAppCompiler(false)} />
      
      <header className="px-6 py-4 border-b border-white/5 bg-gradient-to-r from-[#2C001E]/50 to-transparent">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <Logo />
          <div className="flex items-center gap-2">
            <ToolTab icon={CircuitBoard} label="Kernel Forge" active={activeTool === "kernel"} onClick={() => setActiveTool("kernel")} />
            <ToolTab icon={Package} label="OS Builder" active={activeTool === "os"} onClick={() => setActiveTool("os")} />
            <ToolTab icon={Smartphone} label="Android ROM" active={activeTool === "android"} onClick={() => setActiveTool("android")} color="#3DDC84" />
            <ToolTab icon={Wrench} label="Recovery" active={activeTool === "recovery"} onClick={() => setActiveTool("recovery")} color="#F99B11" />
            <ToolTab icon={Layers} label="Halium" active={activeTool === "halium"} onClick={() => setActiveTool("halium")} />
          </div>
          <div className="flex items-center gap-2">
            <button onClick={() => setShowAppCompiler(!showAppCompiler)} className="btn-primary text-sm">
              <Download className="w-4 h-4 mr-2" /> Get Local App
            </button>
            <button onClick={() => setShowBinaryManager(!showBinaryManager)} className="btn-outline text-sm">
              <Settings className="w-4 h-4 mr-2" /> Binaries
            </button>
            <button onClick={fetchDevices} className="btn-outline text-sm">
              <RefreshCw className="w-4 h-4 mr-2" /> Devices
            </button>
          </div>
        </div>
      </header>

      <main className="flex-1 flex flex-col">
        <PanelGroup direction="vertical">
          <Panel defaultSize={60} minSize={30}>
            <div className="h-full overflow-auto p-6">
              <div className="max-w-7xl mx-auto">
                <div className="grid grid-cols-12 gap-4">
                  <div className="col-span-12 lg:col-span-4">
                    <h2 className="text-lg font-semibold text-white mb-3 flex items-center gap-2">
                      <Smartphone className="w-5 h-5 text-[#E95420]" /> Device
                    </h2>
                    <DevicePanel device={devices[0]} deviceInfo={deviceInfo} onRefresh={fetchDevices} onSelect={handleDeviceSelect} />
                  </div>

                  <div className="col-span-12 lg:col-span-8">
                    <AnimatePresence mode="wait">
                      {activeTool === "kernel" && (
                        <motion.div key="kernel" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }}>
                          <h2 className="text-lg font-semibold text-white mb-3 flex items-center gap-2">
                            <CircuitBoard className="w-5 h-5 text-[#E95420]" /> Kernel Forge
                            <Badge variant="primary">Build • Upstream • Backport</Badge>
                          </h2>
                          <KernelForgePanel deviceInfo={deviceInfo} sessionId={sessionId} />
                        </motion.div>
                      )}
                      {activeTool === "os" && (
                        <motion.div key="os" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }}>
                          <h2 className="text-lg font-semibold text-white mb-3 flex items-center gap-2">
                            <Package className="w-5 h-5 text-[#E95420]" /> OS Image Builder
                            <Badge variant="primary">Any Distro • Any Device</Badge>
                          </h2>
                          <OSImageBuilderPanel deviceInfo={deviceInfo} />
                        </motion.div>
                      )}
                      {activeTool === "android" && (
                        <motion.div key="android" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }}>
                          <h2 className="text-lg font-semibold text-white mb-3 flex items-center gap-2">
                            <Smartphone className="w-5 h-5 text-[#3DDC84]" /> Android ROM Builder
                            <Badge variant="android">AI-Guided</Badge>
                          </h2>
                          <AndroidBuilderPanel deviceInfo={deviceInfo} sessionId={sessionId} />
                        </motion.div>
                      )}
                      {activeTool === "recovery" && (
                        <motion.div key="recovery" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }}>
                          <h2 className="text-lg font-semibold text-white mb-3 flex items-center gap-2">
                            <Wrench className="w-5 h-5 text-[#F99B11]" /> Recovery Builder
                            <Badge variant="warning">TWRP • OrangeFox • More</Badge>
                          </h2>
                          <RecoveryBuilderPanel deviceInfo={deviceInfo} />
                        </motion.div>
                      )}
                      {activeTool === "halium" && (
                        <motion.div key="halium" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }}>
                          <h2 className="text-lg font-semibold text-white mb-3 flex items-center gap-2">
                            <Layers className="w-5 h-5 text-[#E95420]" /> Halium Builder
                            <Badge variant="primary">Android Hybrid</Badge>
                          </h2>
                          <HaliumBuilderPanel deviceInfo={deviceInfo} />
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </div>
                </div>
              </div>
            </div>
          </Panel>

          <PanelResizeHandle className="h-2 bg-transparent hover:bg-[#E95420]/30 transition-colors cursor-row-resize flex items-center justify-center group">
            <div className="w-12 h-1 rounded-full bg-white/10 group-hover:bg-[#E95420]/50" />
          </PanelResizeHandle>

          <Panel defaultSize={40} minSize={20} collapsible>
            <div className="h-full flex flex-col bg-[#0A0A0A] border-t border-white/5">
              <div className="flex items-center justify-between px-4 py-2 bg-black/50 border-b border-white/5">
                <div className="flex items-center gap-4">
                  <button className={`flex items-center gap-2 px-3 py-1.5 rounded text-sm ${bottomPanel === "terminal" ? "bg-[#E95420]/20 text-[#E95420]" : "text-white/50"}`}
                    onClick={() => setBottomPanel("terminal")}>
                    <TerminalSquare className="w-4 h-4" /> Terminal
                  </button>
                  <button className={`flex items-center gap-2 px-3 py-1.5 rounded text-sm ${bottomPanel === "chat" ? "bg-[#77216F]/20 text-[#77216F]" : "text-white/50"}`}
                    onClick={() => setBottomPanel("chat")}>
                    <Bot className="w-4 h-4" /> AI Engineer
                  </button>
                </div>
                <button onClick={() => bottomPanel === "terminal" ? setTerminalHistory([]) : setChatMessages([])} className="text-white/40 hover:text-white p-1">
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
              <div className="flex-1 overflow-hidden">
                {bottomPanel === "terminal" ? (
                  <Terminal history={terminalHistory} onCommand={handleTerminalCommand} isLoading={isTerminalLoading} />
                ) : (
                  <AIChat messages={chatMessages} onSend={handleAiChat} isLoading={isAiLoading} deviceContext={deviceInfo} />
                )}
              </div>
            </div>
          </Panel>
        </PanelGroup>
      </main>

      <Toaster position="bottom-right" toastOptions={{ style: { background: '#2C2025', color: '#F5F5F5', border: '1px solid rgba(255,255,255,0.1)' } }} />
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
