import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Smartphone, RefreshCw, Cpu, HardDrive, Shield, Battery, Info, AlertCircle, CheckCircle2, XCircle, Zap } from 'lucide-react';
import axios from 'axios';
import { toast } from 'sonner';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const DeviceDetectionPanel = ({ onDeviceSelected }) => {
  const [devices, setDevices] = useState([]);
  const [loading, setLoading] = useState(false);
  const [selectedDevice, setSelectedDevice] = useState(null);
  const [expanded, setExpanded] = useState(true);

  useEffect(() => {
    detectDevices();
    // Auto-refresh every 5 seconds
    const interval = setInterval(detectDevices, 5000);
    return () => clearInterval(interval);
  }, []);

  const detectDevices = async () => {
    try {
      const res = await axios.get(`${API}/devices/connected`);
      setDevices(res.data.devices || []);
      
      // Auto-select if only one device
      if (res.data.devices?.length === 1) {
        setSelectedDevice(res.data.devices[0]);
        if (onDeviceSelected) {
          onDeviceSelected(res.data.devices[0]);
        }
      }
    } catch (e) {
      console.error('Failed to detect devices:', e);
    }
  };

  const handleRefresh = async () => {
    setLoading(true);
    await detectDevices();
    setLoading(false);
    toast.success('Devices refreshed');
  };

  const handleSelectDevice = (device) => {
    setSelectedDevice(device);
    if (onDeviceSelected) {
      onDeviceSelected(device);
    }
    toast.success(`Selected: ${device.manufacturer} ${device.model}`);
  };

  return (
    <div className="glass-card rounded-xl p-4 mb-4">
      <div 
        className="flex items-center justify-between cursor-pointer" 
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center gap-2">
          <Smartphone className="w-5 h-5 text-[#E95420]" />
          <h3 className="font-semibold text-white">Connected Devices</h3>
          {devices.length > 0 && (
            <span className="text-xs px-2 py-0.5 rounded-full bg-[#E95420]/20 text-[#E95420]">
              {devices.length}
            </span>
          )}
        </div>
        <button 
          onClick={(e) => { e.stopPropagation(); handleRefresh(); }}
          className="p-2 hover:bg-white/5 rounded-lg transition-all"
          disabled={loading}
        >
          <RefreshCw className={`w-4 h-4 text-white/70 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="mt-4 space-y-2"
          >
            {devices.length === 0 ? (
              <div className="text-center py-8">
                <AlertCircle className="w-12 h-12 text-white/20 mx-auto mb-3" />
                <p className="text-sm text-white/50 mb-2">No devices detected</p>
                <p className="text-xs text-white/30">Connect your device via USB and enable USB debugging</p>
              </div>
            ) : (
              devices.map((device) => (
                <motion.div
                  key={device.serial}
                  whileHover={{ scale: 1.02 }}
                  onClick={() => handleSelectDevice(device)}
                  className={`p-3 rounded-lg cursor-pointer transition-all ${
                    selectedDevice?.serial === device.serial
                      ? 'bg-[#E95420]/20 border-2 border-[#E95420]/50'
                      : 'bg-black/20 border border-white/5 hover:border-white/20'
                  }`}
                >
                  <div className="flex items-start justify-between mb-2">
                    <div>
                      <h4 className="font-semibold text-white text-sm">
                        {device.manufacturer} {device.model}
                      </h4>
                      <p className="text-xs text-white/50">{device.codename}</p>
                    </div>
                    {device.is_rooted && (
                      <span className="text-[9px] px-2 py-0.5 rounded bg-green-500/20 text-green-300 border border-green-500/30">
                        Rooted
                      </span>
                    )}
                  </div>

                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <div className="flex items-center gap-1.5">
                      <Cpu className="w-3 h-3 text-white/40" />
                      <span className="text-white/60">{device.cpu_abi}</span>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <HardDrive className="w-3 h-3 text-white/40" />
                      <span className="text-white/60">Android {device.android_version}</span>
                    </div>
                    {device.kernel_version && (
                      <div className="flex items-center gap-1.5 col-span-2">
                        <Zap className="w-3 h-3 text-white/40" />
                        <span className="text-white/60 text-[10px] truncate">
                          {device.kernel_version.substring(0, 50)}...
                        </span>
                      </div>
                    )}
                  </div>

                  {device.has_custom_recovery && (
                    <div className="mt-2 flex items-center gap-1 text-xs text-purple-400">
                      <CheckCircle2 className="w-3 h-3" />
                      <span>Custom Recovery Detected</span>
                    </div>
                  )}
                </motion.div>
              ))
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default DeviceDetectionPanel;
