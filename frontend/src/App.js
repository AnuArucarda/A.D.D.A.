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
  CircuitBoard, Binary, FolderGit2, Target, ArrowUpCircle, CheckCheck, XOctagon
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
      <p className="text-xs text-white/50">Kernel • OS • Halium</p>
    </div>
  </div>
);

const Badge = ({ variant = "neutral", children, className = "" }) => {
  const variants = {
    success: "badge-success",
    warning: "badge-warning",
    error: "badge-error",
    neutral: "badge-neutral",
    primary: "bg-[#E95420]/20 text-[#E95420] border border-[#E95420]/30"
  };
  return <span className={`badge ${variants[variant]} ${className}`}>{children}</span>;
};

const ToolTab = ({ icon: Icon, label, active, onClick, badge }) => (
  <button
    onClick={onClick}
    className={`flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-all ${
      active
        ? "bg-[#E95420]/20 text-[#E95420] border border-[#E95420]/30"
        : "text-white/60 hover:text-white hover:bg-white/5"
    }`}
    data-testid={`tool-tab-${label.toLowerCase().replace(/\s/g, '-')}`}
  >
    <Icon className="w-4 h-4" />
    {label}
    {badge && <Badge variant="neutral" className="ml-1 text-[10px]">{badge}</Badge>}
  </button>
);

const ConfigItem = ({ config, status, required, description }) => (
  <div className={`flex items-center justify-between p-2 rounded ${
    status === "ok" ? "bg-green-500/10" : status === "missing" ? "bg-red-500/10" : "bg-white/5"
  }`}>
    <div className="flex items-center gap-2">
      {status === "ok" ? (
        <CheckCircle2 className="w-4 h-4 text-green-400" />
      ) : (
        <XCircle className="w-4 h-4 text-red-400" />
      )}
      <span className="font-mono text-xs text-white/80">{config}</span>
      {required && <Badge variant="error" className="text-[8px]">REQ</Badge>}
    </div>
    <span className="text-xs text-white/40">{description}</span>
  </div>
);

const DistroCard = ({ distro, info, selected, onSelect }) => (
  <motion.div
    whileHover={{ scale: 1.02 }}
    onClick={() => onSelect(distro)}
    className={`p-4 rounded-xl cursor-pointer transition-all ${
      selected
        ? "bg-[#E95420]/20 border-2 border-[#E95420]/50"
        : "glass-card hover:border-white/20"
    }`}
    data-testid={`distro-${distro}`}
  >
    <div className="flex items-center gap-3 mb-2">
      <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${
        info.type === "mobile" ? "bg-purple-500/20" : "bg-blue-500/20"
      }`}>
        {info.type === "mobile" ? (
          <Smartphone className="w-4 h-4 text-purple-400" />
        ) : (
          <Monitor className="w-4 h-4 text-blue-400" />
        )}
      </div>
      <div>
        <h4 className="font-semibold text-white text-sm">{info.name}</h4>
        <Badge variant={info.type === "mobile" ? "primary" : "neutral"} className="text-[9px]">
          {info.type}
        </Badge>
      </div>
    </div>
    <p className="text-xs text-white/50 line-clamp-2">{info.description}</p>
    <div className="mt-2 flex items-center gap-2">
      <Badge variant="neutral" className="text-[9px]">{info.init_system || "systemd"}</Badge>
    </div>
  </motion.div>
);

const KernelVersionCard = ({ version, info, selected, onSelect, current }) => (
  <div
    onClick={() => onSelect(version)}
    className={`p-3 rounded-lg cursor-pointer transition-all ${
      selected
        ? "bg-[#E95420]/20 border border-[#E95420]/50"
        : "bg-black/20 border border-white/5 hover:border-white/10"
    } ${current === version ? "ring-2 ring-green-500/50" : ""}`}
    data-testid={`kernel-version-${version}`}
  >
    <div className="flex items-center justify-between">
      <span className="font-mono text-sm text-white">{version}</span>
      <Badge variant={info.status === "lts" ? "success" : info.status === "mainline" ? "primary" : "warning"}>
        {info.status}
      </Badge>
    </div>
    {current === version && (
      <span className="text-[10px] text-green-400">Current</span>
    )}
  </div>
);

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
        <button onClick={onRefresh} className="btn-outline text-xs mt-4" data-testid="scan-devices-btn">
          <RefreshCw className="w-3.5 h-3.5 mr-1.5" />
          Scan Devices
        </button>
      </div>
    );
  }

  return (
    <div className="glass-card rounded-xl p-5" data-testid="device-panel">
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
            device.state === "device" ? "bg-green-500/20" : "bg-yellow-500/20"
          }`}>
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
        <div className="flex items-center gap-2 text-white/40">
          <Loader2 className="w-4 h-4 animate-spin" />
          Loading device info...
        </div>
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
          
          {deviceInfo.kernel_version_parsed && (
            <div className="bg-black/20 rounded p-2">
              <span className="text-white/40 text-xs">Kernel</span>
              <p className="text-white font-mono text-sm">
                {deviceInfo.kernel_version_parsed.version || "Unknown"}
              </p>
            </div>
          )}

          <div className="flex gap-2 mt-3">
            <button onClick={fetchInfo} className="btn-outline text-xs py-1.5 flex-1" data-testid="refresh-info-btn">
              <RefreshCw className="w-3 h-3 mr-1" /> Refresh
            </button>
            <button onClick={onRefresh} className="btn-outline text-xs py-1.5 flex-1">
              <HardDrive className="w-3 h-3 mr-1" /> Scan All
            </button>
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
  const [targetVersion, setTargetVersion] = useState("6.6");
  const [upstreamAnalysis, setUpstreamAnalysis] = useState(null);
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
    } catch (e) {
      console.error("Failed to fetch kernel projects");
    }
  };

  const fetchMainlineVersions = async () => {
    try {
      const res = await axios.get(`${API}/kernel/mainline-versions`);
      setMainlineVersions(res.data.versions);
    } catch (e) {
      console.error("Failed to fetch mainline versions");
    }
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
      toast.error("Failed to analyze kernel config");
    } finally {
      setLoading(false);
    }
  };

  const analyzeUpstream = async () => {
    if (!selectedProject) return;
    setLoading(true);
    try {
      const res = await axios.post(`${API}/kernel/projects/${selectedProject.id}/analyze-upstream?target_version=${targetVersion}`);
      setUpstreamAnalysis(res.data);
    } catch (e) {
      toast.error("Failed to analyze upstream compatibility");
    } finally {
      setLoading(false);
    }
  };

  const fixConfig = async () => {
    if (!selectedProject) return;
    setLoading(true);
    try {
      const res = await axios.post(`${API}/kernel/projects/${selectedProject.id}/fix-config`);
      if (res.data.success) {
        setConfigAnalysis(res.data.new_analysis);
        toast.success("Config fixes applied");
      }
    } catch (e) {
      toast.error("Failed to apply config fixes");
    } finally {
      setLoading(false);
    }
  };

  const compileKernel = async () => {
    if (!selectedProject) return;
    try {
      await axios.post(`${API}/kernel/projects/${selectedProject.id}/compile`);
      toast.success("Kernel compilation started");
    } catch (e) {
      toast.error("Failed to start compilation");
    }
  };

  return (
    <div className="space-y-4" data-testid="kernel-forge-panel">
      {/* Project Creation */}
      <div className="glass-card rounded-xl p-5">
        <h3 className="font-semibold text-white flex items-center gap-2 mb-4">
          <FolderGit2 className="w-4 h-4 text-[#E95420]" />
          Kernel Project
        </h3>
        
        <div className="space-y-3">
          <input
            type="text"
            placeholder="Kernel source URL (git)"
            value={kernelSource}
            onChange={(e) => setKernelSource(e.target.value)}
            className="input-dark w-full text-sm"
            data-testid="kernel-source-input"
          />
          <button
            onClick={createProject}
            disabled={loading || (!deviceInfo?.codename && !deviceInfo?.device)}
            className="btn-primary w-full flex items-center justify-center gap-2"
            data-testid="create-kernel-project-btn"
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <GitBranch className="w-4 h-4" />}
            Create Kernel Project
          </button>
        </div>

        {projects.length > 0 && (
          <div className="mt-4">
            <label className="text-xs text-white/50 mb-2 block">Existing Projects</label>
            <div className="space-y-2 max-h-32 overflow-y-auto">
              {projects.map((p) => (
                <div
                  key={p.id}
                  onClick={() => setSelectedProject(p)}
                  className={`p-2 rounded cursor-pointer ${
                    selectedProject?.id === p.id ? "bg-[#E95420]/20 border border-[#E95420]/30" : "bg-black/20"
                  }`}
                >
                  <span className="text-sm text-white">{p.name}</span>
                  <Badge variant="neutral" className="ml-2 text-[9px]">{p.build_status}</Badge>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Config Analysis */}
      {selectedProject && (
        <div className="glass-card rounded-xl p-5">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-white flex items-center gap-2">
              <Cog className="w-4 h-4 text-[#E95420]" />
              Kernel Config Analysis
            </h3>
            <button onClick={analyzeConfig} className="btn-outline text-xs" data-testid="analyze-config-btn">
              {loading ? <Loader2 className="w-3 h-3 animate-spin" /> : "Analyze"}
            </button>
          </div>

          {configAnalysis && (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-white/60 text-sm">Compatibility Score</span>
                <div className="flex items-center gap-2">
                  <div className="w-24 h-2 bg-black/30 rounded-full overflow-hidden">
                    <div
                      className={`h-full ${configAnalysis.compatibility_score >= 80 ? "bg-green-500" : configAnalysis.compatibility_score >= 50 ? "bg-yellow-500" : "bg-red-500"}`}
                      style={{ width: `${configAnalysis.compatibility_score}%` }}
                    />
                  </div>
                  <span className="text-white font-mono text-sm">{configAnalysis.compatibility_score}%</span>
                </div>
              </div>

              <div className="flex items-center gap-2">
                {configAnalysis.linux_ready ? (
                  <Badge variant="success">Linux Ready</Badge>
                ) : (
                  <Badge variant="error">Needs Config Fixes</Badge>
                )}
              </div>

              {configAnalysis.missing?.length > 0 && (
                <div className="mt-3">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs text-white/50">Missing Configs ({configAnalysis.missing.length})</span>
                    <button onClick={fixConfig} className="text-xs text-[#E95420] hover:underline" data-testid="fix-config-btn">
                      Auto-Fix
                    </button>
                  </div>
                  <div className="space-y-1 max-h-40 overflow-y-auto">
                    {configAnalysis.missing.slice(0, 10).map((m, i) => (
                      <ConfigItem key={i} {...m} status="missing" />
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Upstream Analysis */}
      {selectedProject && (
        <div className="glass-card rounded-xl p-5">
          <h3 className="font-semibold text-white flex items-center gap-2 mb-4">
            <ArrowUpCircle className="w-4 h-4 text-[#E95420]" />
            Kernel Upstreaming
          </h3>

          <div className="grid grid-cols-3 gap-2 mb-4">
            {Object.entries(mainlineVersions).slice(0, 6).map(([ver, info]) => (
              <KernelVersionCard
                key={ver}
                version={ver}
                info={info}
                selected={targetVersion === ver}
                onSelect={setTargetVersion}
                current={deviceInfo?.kernel_version_parsed?.version}
              />
            ))}
          </div>

          <button onClick={analyzeUpstream} className="btn-outline w-full text-sm" data-testid="analyze-upstream-btn">
            <Target className="w-4 h-4 mr-2" />
            Analyze Upgrade Path to {targetVersion}
          </button>

          {upstreamAnalysis && (
            <div className="mt-4 p-3 bg-black/20 rounded-lg">
              <div className="flex items-center justify-between mb-2">
                <span className="text-white/60 text-sm">
                  {upstreamAnalysis.current_version} → {upstreamAnalysis.target_version}
                </span>
                <Badge variant={upstreamAnalysis.estimated_effort === "low" ? "success" : upstreamAnalysis.estimated_effort === "medium" ? "warning" : "error"}>
                  {upstreamAnalysis.estimated_effort} effort
                </Badge>
              </div>
              <div className="text-xs text-white/50">
                Compatibility: {upstreamAnalysis.compatibility_score}%
              </div>
              {upstreamAnalysis.breaking_changes?.length > 0 && (
                <div className="mt-2 text-xs text-red-400">
                  ⚠️ {upstreamAnalysis.breaking_changes.length} breaking changes
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Build Actions */}
      {selectedProject && (
        <div className="glass-card rounded-xl p-5">
          <h3 className="font-semibold text-white flex items-center gap-2 mb-4">
            <Hammer className="w-4 h-4 text-[#E95420]" />
            Build Kernel
          </h3>
          <div className="flex gap-2">
            <button onClick={compileKernel} className="btn-primary flex-1" data-testid="compile-kernel-btn">
              <Zap className="w-4 h-4 mr-2" />
              Compile Kernel
            </button>
            <button className="btn-outline" data-testid="generate-dt-btn">
              <FileCode className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

// ======================= OS IMAGE BUILDER PANEL =======================

const OSImageBuilderPanel = ({ deviceInfo, sessionId }) => {
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
    } catch (e) {
      console.error("Failed to fetch distros");
    }
  };

  const fetchProjects = async () => {
    try {
      const res = await axios.get(`${API}/os/projects`);
      setProjects(res.data.projects);
    } catch (e) {
      console.error("Failed to fetch OS projects");
    }
  };

  const createOSProject = async () => {
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
      toast.success("OS image project created");
    } catch (e) {
      toast.error("Failed to create project");
    } finally {
      setLoading(false);
    }
  };

  const startBuild = async (projectId) => {
    try {
      await axios.post(`${API}/os/projects/${projectId}/build`);
      toast.success("OS image build started");
    } catch (e) {
      toast.error("Failed to start build");
    }
  };

  const currentDistros = distroType === "mobile" ? distros.mobile : distros.desktop;

  return (
    <div className="space-y-4" data-testid="os-builder-panel">
      {/* Distro Selection */}
      <div className="glass-card rounded-xl p-5">
        <h3 className="font-semibold text-white flex items-center gap-2 mb-4">
          <Package className="w-4 h-4 text-[#E95420]" />
          Select Distribution
        </h3>

        <div className="flex gap-2 mb-4">
          <button
            onClick={() => setDistroType("mobile")}
            className={`flex-1 py-2 rounded-lg text-sm font-medium transition-all ${
              distroType === "mobile"
                ? "bg-purple-500/20 text-purple-400 border border-purple-500/30"
                : "bg-black/20 text-white/60"
            }`}
          >
            <Smartphone className="w-4 h-4 inline mr-2" />
            Mobile ({Object.keys(distros.mobile || {}).length})
          </button>
          <button
            onClick={() => setDistroType("desktop")}
            className={`flex-1 py-2 rounded-lg text-sm font-medium transition-all ${
              distroType === "desktop"
                ? "bg-blue-500/20 text-blue-400 border border-blue-500/30"
                : "bg-black/20 text-white/60"
            }`}
          >
            <Monitor className="w-4 h-4 inline mr-2" />
            Desktop ({Object.keys(distros.desktop || {}).length})
          </button>
        </div>

        <div className="grid grid-cols-2 gap-3 max-h-64 overflow-y-auto">
          {Object.entries(currentDistros).map(([key, info]) => (
            <DistroCard
              key={key}
              distro={key}
              info={info}
              selected={selectedDistro === key}
              onSelect={setSelectedDistro}
            />
          ))}
        </div>

        <button
          onClick={createOSProject}
          disabled={!selectedDistro || !deviceInfo || loading}
          className="btn-primary w-full mt-4"
          data-testid="create-os-project-btn"
        >
          {loading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Box className="w-4 h-4 mr-2" />}
          Create OS Image Project
        </button>
      </div>

      {/* Custom Upload */}
      <div className="glass-card rounded-xl p-5">
        <h3 className="font-semibold text-white flex items-center gap-2 mb-4">
          <Upload className="w-4 h-4 text-[#E95420]" />
          Custom Rootfs Upload
        </h3>
        <p className="text-xs text-white/50 mb-3">
          Upload your own rootfs archive (.tar.gz, .tar.xz, .zip)
        </p>
        <label className="block">
          <div className="border-2 border-dashed border-white/10 rounded-lg p-6 text-center cursor-pointer hover:border-white/20 transition-colors">
            <Upload className="w-8 h-8 text-white/30 mx-auto mb-2" />
            <span className="text-sm text-white/40">Click to upload or drag and drop</span>
          </div>
          <input type="file" className="hidden" accept=".tar.gz,.tar.xz,.tar.bz2,.zip" />
        </label>
      </div>

      {/* Projects */}
      {projects.length > 0 && (
        <div className="glass-card rounded-xl p-5">
          <h3 className="font-semibold text-white flex items-center gap-2 mb-4">
            <Database className="w-4 h-4 text-[#E95420]" />
            OS Image Projects
          </h3>
          <div className="space-y-2">
            {projects.map((p) => (
              <div key={p.id} className="flex items-center justify-between p-3 bg-black/20 rounded-lg">
                <div>
                  <span className="text-white text-sm">{p.name}</span>
                  <div className="flex items-center gap-2 mt-1">
                    <Badge variant="neutral" className="text-[9px]">{p.distro}</Badge>
                    <Badge variant={p.build_status === "completed" ? "success" : "warning"} className="text-[9px]">
                      {p.build_status}
                    </Badge>
                  </div>
                </div>
                <button
                  onClick={() => startBuild(p.id)}
                  className="btn-outline text-xs"
                  disabled={p.build_status === "building"}
                >
                  {p.build_status === "building" ? (
                    <Loader2 className="w-3 h-3 animate-spin" />
                  ) : (
                    <Play className="w-3 h-3" />
                  )}
                </button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

// ======================= HALIUM BUILDER PANEL =======================

const HaliumBuilderPanel = ({ deviceInfo, sessionId }) => {
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
    } catch (e) {
      console.error("Failed to fetch Halium versions");
    }
  };

  const fetchBuilds = async () => {
    try {
      const res = await axios.get(`${API}/halium/builds`);
      setBuilds(res.data.builds || []);
    } catch (e) {
      console.error("Failed to fetch Halium builds");
    }
  };

  const startBuild = async () => {
    if (!deviceInfo?.serial) {
      toast.error("Connect a device first");
      return;
    }
    setLoading(true);
    try {
      await axios.post(`${API}/halium/build`, {
        device_serial: deviceInfo.serial,
        halium_version: selectedVersion
      });
      toast.success("Halium build started");
      fetchBuilds();
    } catch (e) {
      toast.error("Failed to start build");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-4" data-testid="halium-builder-panel">
      <div className="glass-card rounded-xl p-5">
        <h3 className="font-semibold text-white flex items-center gap-2 mb-4">
          <Layers className="w-4 h-4 text-[#E95420]" />
          Halium Version
        </h3>
        <div className="grid grid-cols-2 gap-2">
          {haliumVersions.map((v) => (
            <button
              key={v.id}
              onClick={() => setSelectedVersion(v.id)}
              className={`p-3 rounded-lg text-left transition-all ${
                selectedVersion === v.id
                  ? "bg-[#E95420]/20 border border-[#E95420]/50"
                  : "bg-black/20 border border-white/5 hover:border-white/10"
              }`}
              data-testid={`halium-${v.id}`}
            >
              <div className="font-medium text-sm text-white">{v.name}</div>
              <div className="text-xs text-white/40">{v.android_base}</div>
              <Badge variant={v.status === "latest" ? "success" : "neutral"} className="mt-1 text-[9px]">
                {v.status}
              </Badge>
            </button>
          ))}
        </div>
      </div>

      <div className="glass-card rounded-xl p-5">
        <h3 className="font-semibold text-white flex items-center gap-2 mb-4">
          <Hammer className="w-4 h-4 text-[#E95420]" />
          Build Halium
        </h3>
        <button
          onClick={startBuild}
          disabled={!deviceInfo || loading}
          className="btn-primary w-full"
          data-testid="start-halium-build-btn"
        >
          {loading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Zap className="w-4 h-4 mr-2" />}
          Start Halium Build
        </button>
      </div>

      {builds.length > 0 && (
        <div className="glass-card rounded-xl p-5">
          <h3 className="font-semibold text-white flex items-center gap-2 mb-4">
            <ScrollText className="w-4 h-4 text-[#E95420]" />
            Build History
          </h3>
          <div className="space-y-2 max-h-48 overflow-y-auto">
            {builds.map((b) => (
              <div key={b.id} className="p-3 bg-black/20 rounded-lg">
                <div className="flex items-center justify-between">
                  <span className="text-white text-sm">{b.device_codename || b.device_serial}</span>
                  <Badge variant={b.status === "completed" ? "success" : b.status === "failed" ? "error" : "warning"}>
                    {b.status}
                  </Badge>
                </div>
                <div className="text-xs text-white/40 mt-1">{b.halium_version}</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

// ======================= TERMINAL & AI CHAT =======================

const Terminal = ({ history, onCommand, isLoading }) => {
  const [input, setInput] = useState("");
  const terminalRef = useRef(null);

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

  return (
    <div className="flex flex-col h-full bg-[#0A0A0A] rounded-lg overflow-hidden" data-testid="terminal">
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
          </div>
        ))}
        {isLoading && (
          <div className="flex items-center gap-2 text-white/40">
            <Loader2 className="w-4 h-4 animate-spin" />
            Executing...
          </div>
        )}
      </div>

      <form onSubmit={handleSubmit} className="p-3 border-t border-white/5 bg-black/30">
        <div className="flex items-center gap-2">
          <span className="terminal-prompt">❯</span>
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Enter command..."
            className="flex-1 bg-transparent outline-none text-[#38D878] font-mono placeholder:text-white/20"
            disabled={isLoading}
            data-testid="terminal-input"
          />
          <button type="submit" disabled={isLoading || !input.trim()} className="p-2 rounded hover:bg-white/5 text-white/40 hover:text-white disabled:opacity-30">
            <Play className="w-4 h-4" />
          </button>
        </div>
      </form>
    </div>
  );
};

const AIChat = ({ messages, onSend, isLoading, deviceContext, kernelContext }) => {
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
    toast.success("Copied");
  };

  const formatMessage = (content) => {
    const parts = content.split(/(```[\s\S]*?```)/g);
    return parts.map((part, i) => {
      if (part.startsWith("```") && part.endsWith("```")) {
        const code = part.slice(3, -3).replace(/^(bash|sh|shell)\n/, "");
        return (
          <div key={i} className="relative group my-2">
            <pre className="bg-black/40 border border-white/10 rounded-lg p-4 overflow-x-auto">
              <code className="text-[#38D878] text-sm">{code}</code>
            </pre>
            <button onClick={() => copyToClipboard(code)} className="absolute top-2 right-2 p-1.5 rounded bg-white/5 opacity-0 group-hover:opacity-100 transition-opacity">
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
            <p className="text-white/40 text-sm">Ask about kernel development, OS building, or device porting</p>
            <div className="mt-4 flex flex-wrap gap-2 justify-center">
              {["Analyze my kernel config", "How to upstream to 6.6?", "Build Ubuntu Touch rootfs"].map((q) => (
                <button key={q} onClick={() => setInput(q)} className="text-xs px-3 py-1.5 rounded-full bg-white/5 text-white/60 hover:bg-white/10">
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg, i) => (
          <motion.div key={i} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className={msg.role === "user" ? "ml-8" : "mr-8"}>
            <div className={`rounded-xl p-4 ${msg.role === "user" ? "bg-[#E95420]/20 border border-[#E95420]/30" : "bg-black/30 border border-white/5"}`}>
              <div className="flex items-center gap-2 mb-2">
                {msg.role === "assistant" ? <Bot className="w-4 h-4 text-[#77216F]" /> : <span className="text-[#E95420] text-xs font-mono">you@forge</span>}
                <span className="text-xs text-white/30">{new Date(msg.timestamp).toLocaleTimeString()}</span>
              </div>
              <div className="ai-message">{formatMessage(msg.content)}</div>
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
            placeholder="Ask about kernel, OS, or device porting..."
            className="input-dark flex-1"
            disabled={isLoading}
            data-testid="ai-chat-input"
          />
          <button type="submit" disabled={isLoading || !input.trim()} className="btn-primary flex items-center gap-2" data-testid="ai-chat-submit">
            <Send className="w-4 h-4" />
          </button>
        </div>
      </form>
    </div>
  );
};

// ======================= MAIN DASHBOARD =======================

const Dashboard = () => {
  const [activeTool, setActiveTool] = useState("kernel"); // kernel, os, halium
  const [devices, setDevices] = useState([]);
  const [selectedDevice, setSelectedDevice] = useState(null);
  const [deviceInfo, setDeviceInfo] = useState(null);
  const [terminalHistory, setTerminalHistory] = useState([]);
  const [chatMessages, setChatMessages] = useState([]);
  const [isTerminalLoading, setIsTerminalLoading] = useState(false);
  const [isAiLoading, setIsAiLoading] = useState(false);
  const [bottomPanel, setBottomPanel] = useState("terminal"); // terminal, chat
  const [sessionId] = useState(() => `session-${Date.now()}`);

  useEffect(() => {
    fetchDevices();
    checkHealth();
  }, []);

  const checkHealth = async () => {
    try {
      const res = await axios.get(`${API}/health`);
      if (res.data.kernel_forge_ready) {
        addTerminalEntry("output", "Linux Device Forge ready. Kernel tools available.");
      }
    } catch (e) {
      addTerminalEntry("error", "Failed to connect to backend");
    }
  };

  const fetchDevices = async () => {
    try {
      const res = await axios.get(`${API}/devices`);
      setDevices(res.data.devices);
    } catch (e) {
      console.error("Failed to fetch devices");
    }
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
      const res = await axios.post(`${API}/ai/chat`, {
        message,
        session_id: sessionId,
        device_context: deviceInfo,
        auto_execute: autoExecute
      });

      setChatMessages((prev) => [...prev, {
        role: "assistant",
        content: res.data.response,
        extracted_commands: res.data.extracted_commands,
        timestamp: new Date().toISOString()
      }]);

      if (autoExecute && res.data.extracted_commands?.length > 0) {
        for (const cmd of res.data.extracted_commands) {
          await handleTerminalCommand(cmd);
        }
      }
    } catch (e) {
      toast.error("AI chat failed");
    } finally {
      setIsAiLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col" data-testid="dashboard">
      {/* Header */}
      <header className="px-6 py-4 border-b border-white/5 bg-gradient-to-r from-[#2C001E]/50 to-transparent">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <Logo />
          <div className="flex items-center gap-2">
            <ToolTab icon={CircuitBoard} label="Kernel Forge" active={activeTool === "kernel"} onClick={() => setActiveTool("kernel")} />
            <ToolTab icon={Package} label="OS Builder" active={activeTool === "os"} onClick={() => setActiveTool("os")} />
            <ToolTab icon={Layers} label="Halium" active={activeTool === "halium"} onClick={() => setActiveTool("halium")} />
          </div>
          <button onClick={fetchDevices} className="btn-outline text-sm" data-testid="refresh-devices-btn">
            <RefreshCw className="w-4 h-4 mr-2" />
            Refresh Devices
          </button>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 flex flex-col">
        <PanelGroup direction="vertical">
          <Panel defaultSize={60} minSize={30}>
            <div className="h-full overflow-auto p-6">
              <div className="max-w-7xl mx-auto">
                <div className="grid grid-cols-12 gap-4">
                  {/* Device Panel */}
                  <div className="col-span-12 lg:col-span-4">
                    <h2 className="text-lg font-semibold text-white mb-3 flex items-center gap-2">
                      <Smartphone className="w-5 h-5 text-[#E95420]" />
                      Device
                    </h2>
                    <DevicePanel
                      device={devices[0]}
                      deviceInfo={deviceInfo}
                      onRefresh={fetchDevices}
                      onSelect={handleDeviceSelect}
                    />
                  </div>

                  {/* Tool Panel */}
                  <div className="col-span-12 lg:col-span-8">
                    <AnimatePresence mode="wait">
                      {activeTool === "kernel" && (
                        <motion.div key="kernel" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }}>
                          <h2 className="text-lg font-semibold text-white mb-3 flex items-center gap-2">
                            <CircuitBoard className="w-5 h-5 text-[#E95420]" />
                            Kernel Forge
                            <Badge variant="primary">Build • Upstream • Backport</Badge>
                          </h2>
                          <KernelForgePanel deviceInfo={deviceInfo} sessionId={sessionId} />
                        </motion.div>
                      )}
                      {activeTool === "os" && (
                        <motion.div key="os" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }}>
                          <h2 className="text-lg font-semibold text-white mb-3 flex items-center gap-2">
                            <Package className="w-5 h-5 text-[#E95420]" />
                            OS Image Builder
                            <Badge variant="primary">Any Distro • Any Device</Badge>
                          </h2>
                          <OSImageBuilderPanel deviceInfo={deviceInfo} sessionId={sessionId} />
                        </motion.div>
                      )}
                      {activeTool === "halium" && (
                        <motion.div key="halium" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }}>
                          <h2 className="text-lg font-semibold text-white mb-3 flex items-center gap-2">
                            <Layers className="w-5 h-5 text-[#E95420]" />
                            Halium Builder
                            <Badge variant="primary">Android Hybrid</Badge>
                          </h2>
                          <HaliumBuilderPanel deviceInfo={deviceInfo} sessionId={sessionId} />
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </div>
                </div>
              </div>
            </div>
          </Panel>

          <PanelResizeHandle className="h-2 bg-transparent hover:bg-[#E95420]/30 transition-colors cursor-row-resize flex items-center justify-center group">
            <div className="w-12 h-1 rounded-full bg-white/10 group-hover:bg-[#E95420]/50 transition-colors" />
          </PanelResizeHandle>

          <Panel defaultSize={40} minSize={20} collapsible>
            <div className="h-full flex flex-col bg-[#0A0A0A] border-t border-white/5">
              <div className="flex items-center justify-between px-4 py-2 bg-black/50 border-b border-white/5">
                <div className="flex items-center gap-4">
                  <button
                    className={`flex items-center gap-2 px-3 py-1.5 rounded text-sm ${bottomPanel === "terminal" ? "bg-[#E95420]/20 text-[#E95420]" : "text-white/50"}`}
                    onClick={() => setBottomPanel("terminal")}
                  >
                    <TerminalSquare className="w-4 h-4" /> Terminal
                  </button>
                  <button
                    className={`flex items-center gap-2 px-3 py-1.5 rounded text-sm ${bottomPanel === "chat" ? "bg-[#77216F]/20 text-[#77216F]" : "text-white/50"}`}
                    onClick={() => setBottomPanel("chat")}
                  >
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
