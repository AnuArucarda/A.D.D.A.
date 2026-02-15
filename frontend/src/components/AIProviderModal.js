import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Bot, Lock, XCircle, CheckCircle2, Info, ExternalLink, Loader2, Sparkles } from 'lucide-react';
import axios from 'axios';
import { toast } from 'sonner';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const AIProviderModal = ({ show, onClose, onProviderSelected }) => {
  const [providers, setProviders] = useState({});
  const [selectedProvider, setSelectedProvider] = useState('emergent');
  const [selectedModel, setSelectedModel] = useState('');
  const [apiKey, setApiKey] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [providerStatus, setProviderStatus] = useState({});

  useEffect(() => {
    if (show) {
      fetchProviders();
    }
  }, [show]);

  const fetchProviders = async () => {
    try {
      const res = await axios.get(`${API}/ai-providers`);
      setProviders(res.data.providers);
      setSelectedProvider(res.data.default_provider);
      
      // Set default model for selected provider
      if (res.data.providers[res.data.default_provider]?.models?.length > 0) {
        setSelectedModel(res.data.providers[res.data.default_provider].default_model);
      }
      
      // Check status for each provider
      checkProvidersStatus(Object.keys(res.data.providers));
    } catch (e) {
      toast.error('Failed to fetch AI providers');
    } finally {
      setLoading(false);
    }
  };

  const checkProvidersStatus = async (providerKeys) => {
    const statuses = {};
    for (const key of providerKeys) {
      try {
        const res = await axios.get(`${API}/ai-providers/${key}/status`);
        statuses[key] = res.data;
      } catch (e) {
        statuses[key] = { is_ready: false, message: 'Error checking status' };
      }
    }
    setProviderStatus(statuses);
  };

  const handleProviderChange = (provider) => {
    setSelectedProvider(provider);
    if (providers[provider]?.models?.length > 0) {
      setSelectedModel(providers[provider].default_model);
    }
    setApiKey('');
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const currentProvider = providers[selectedProvider];
      
      // If provider requires API key and it's not built-in, save it
      if (currentProvider?.requires_api_key && !currentProvider?.built_in && apiKey) {
        await axios.post(`${API}/ai-providers/${selectedProvider}/set-credential`, null, {
          params: { api_key: apiKey }
        });
      }
      
      // Notify parent component
      if (onProviderSelected) {
        onProviderSelected({
          provider: selectedProvider,
          model: selectedModel,
          name: currentProvider?.name
        });
      }
      
      toast.success(`${currentProvider?.name} configured successfully!`);
      onClose();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Failed to save configuration');
    } finally {
      setSaving(false);
    }
  };

  if (!show) return null;

  const currentProvider = providers[selectedProvider] || {};
  const status = providerStatus[selectedProvider] || {};

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm" onClick={onClose}>
      <motion.div 
        initial={{ opacity: 0, scale: 0.95 }} 
        animate={{ opacity: 1, scale: 1 }}
        onClick={(e) => e.stopPropagation()}
        className="glass-card rounded-2xl p-6 max-w-5xl w-full mx-4 max-h-[90vh] overflow-y-auto">
        
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-bold text-white flex items-center gap-2">
            <Bot className="w-7 h-7 text-[#E95420]" />
            Choose Your AI Assistant
          </h2>
          <button onClick={onClose} className="text-white/50 hover:text-white">
            <XCircle className="w-6 h-6" />
          </button>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-8 h-8 animate-spin text-[#E95420]" />
          </div>
        ) : (
          <>
            <p className="text-sm text-white/60 mb-6">
              Select which AI model you want to use for build assistance, code generation, and configuration. 
              You can use the built-in Emergent LLM (no setup required) or bring your own API keys.
            </p>

            {/* Provider Grid */}
            <div className="grid grid-cols-2 gap-3 mb-6">
              {Object.entries(providers).map(([key, info]) => {
                const isSelected = selectedProvider === key;
                const isReady = status.is_ready;
                
                return (
                  <motion.div
                    key={key}
                    whileHover={{ scale: 1.02 }}
                    onClick={() => handleProviderChange(key)}
                    className={`p-4 rounded-xl cursor-pointer transition-all ${
                      isSelected 
                        ? 'bg-[#E95420]/20 border-2 border-[#E95420]/50' 
                        : 'bg-black/30 border border-white/5 hover:border-white/20'
                    }`}
                  >
                    <div className="flex items-start justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <Bot className="w-5 h-5 text-white" />
                        <span className="font-semibold text-white text-sm">{info.name}</span>
                      </div>
                      {isReady ? (
                        <CheckCircle2 className="w-4 h-4 text-green-400" />
                      ) : info.built_in ? (
                        <CheckCircle2 className="w-4 h-4 text-green-400" />
                      ) : (
                        <Lock className="w-4 h-4 text-yellow-400" />
                      )}
                    </div>
                    <p className="text-xs text-white/50 mb-2">{info.description}</p>
                    <div className="flex gap-1 flex-wrap">
                      {info.built_in && (
                        <span className="text-[9px] px-2 py-0.5 rounded bg-green-500/20 text-green-300 border border-green-500/30">
                          Built-in
                        </span>
                      )}
                      {info.local && (
                        <span className="text-[9px] px-2 py-0.5 rounded bg-blue-500/20 text-blue-300 border border-blue-500/30">
                          Local
                        </span>
                      )}
                      {!info.requires_api_key && !info.built_in && (
                        <span className="text-[9px] px-2 py-0.5 rounded bg-purple-500/20 text-purple-300 border border-purple-500/30">
                          No API Key
                        </span>
                      )}
                    </div>
                  </motion.div>
                );
              })}
            </div>

            {/* Configuration Section */}
            <div className="space-y-4">
              {/* Model Selection */}
              {currentProvider.models && currentProvider.models.length > 0 && (
                <div>
                  <label className="text-xs text-white/50 mb-2 block">Select Model</label>
                  <select 
                    value={selectedModel} 
                    onChange={(e) => setSelectedModel(e.target.value)}
                    className="w-full px-4 py-2.5 rounded-lg bg-black/40 border border-white/10 text-white focus:border-[#E95420]/50 focus:outline-none"
                  >
                    {currentProvider.models.map(model => (
                      <option key={model} value={model}>{model}</option>
                    ))}
                  </select>
                </div>
              )}

              {/* API Key Input */}
              {currentProvider.requires_api_key && !currentProvider.built_in && (
                <div>
                  <label className="text-xs text-white/50 mb-2 block flex items-center gap-2">
                    API Key <Lock className="w-3 h-3" />
                  </label>
                  <input 
                    type="password" 
                    value={apiKey} 
                    onChange={(e) => setApiKey(e.target.value)}
                    placeholder="Enter your API key"
                    className="w-full px-4 py-2.5 rounded-lg bg-black/40 border border-white/10 text-white placeholder-white/30 focus:border-[#E95420]/50 focus:outline-none"
                  />
                  {currentProvider.auth_url && (
                    <a 
                      href={currentProvider.auth_url} 
                      target="_blank" 
                      rel="noopener noreferrer"
                      className="text-xs text-[#E95420] hover:text-[#E95420]/80 mt-2 inline-flex items-center gap-1"
                    >
                      <ExternalLink className="w-3 h-3" />
                      Get API Key
                    </a>
                  )}
                  <p className="text-xs text-white/40 mt-2">
                    {currentProvider.auth_instructions}
                  </p>
                </div>
              )}

              {/* Status Messages */}
              {currentProvider.built_in && (
                <div className="p-3 bg-green-500/10 border border-green-500/30 rounded-lg">
                  <p className="text-sm text-green-300 flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4" />
                    Using Emergent LLM - No setup required! Ready to use.
                  </p>
                </div>
              )}

              {currentProvider.local && (
                <div className="p-3 bg-blue-500/10 border border-blue-500/30 rounded-lg">
                  <p className="text-sm text-blue-300 flex items-center gap-2">
                    <Info className="w-4 h-4" />
                    {currentProvider.setup_instructions}
                  </p>
                </div>
              )}

              {/* Provider Info */}
              <div className="grid grid-cols-2 gap-3 p-4 bg-black/20 rounded-lg">
                <div>
                  <p className="text-xs text-white/50">Features</p>
                  <div className="flex flex-wrap gap-1 mt-1">
                    {currentProvider.features?.map(feature => (
                      <span key={feature} className="text-[10px] px-2 py-0.5 rounded bg-white/5 text-white/70">
                        {feature}
                      </span>
                    ))}
                  </div>
                </div>
                <div>
                  <p className="text-xs text-white/50">Cost</p>
                  <p className="text-sm text-white mt-1">{currentProvider.cost}</p>
                </div>
              </div>
            </div>

            {/* Save Button */}
            <button 
              onClick={handleSave}
              disabled={saving || (currentProvider.requires_api_key && !currentProvider.built_in && !apiKey)}
              className="w-full mt-6 py-3 rounded-xl font-semibold flex items-center justify-center gap-2 bg-[#E95420] text-white hover:bg-[#E95420]/90 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {saving ? (
                <><Loader2 className="w-5 h-5 animate-spin" /> Configuring...</>
              ) : (
                <><Sparkles className="w-5 h-5" /> Use {currentProvider.name}</>
              )}
            </button>
          </>
        )}
      </motion.div>
    </div>
  );
};

export default AIProviderModal;
