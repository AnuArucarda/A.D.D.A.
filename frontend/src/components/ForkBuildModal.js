import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { GitBranch, XCircle, CheckCircle2, Loader2, Search, Calendar, Cpu, Smartphone } from 'lucide-react';
import axios from 'axios';
import { toast } from 'sonner';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const ForkBuildModal = ({ show, onClose, buildType, deviceCodename, onForkSelected }) => {
  const [builds, setBuilds] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedBuild, setSelectedBuild] = useState(null);

  useEffect(() => {
    if (show) {
      fetchBuilds();
    }
  }, [show, buildType, deviceCodename]);

  const fetchBuilds = async () => {
    setLoading(true);
    try {
      const params = { limit: 50 };
      if (deviceCodename) {
        params.device_codename = deviceCodename;
      }
      
      const res = await axios.get(`${API}/builds/${buildType}/successful`, { params });
      setBuilds(res.data.builds || []);
    } catch (e) {
      toast.error('Failed to fetch builds');
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleFork = async () => {
    if (!selectedBuild) {
      toast.error('Please select a build to fork');
      return;
    }

    try {
      const res = await axios.post(`${API}/builds/${selectedBuild.build_id}/fork`, {
        modifications: {}
      });
      
      if (onForkSelected) {
        onForkSelected(res.data);
      }
      
      toast.success('Build forked successfully!');
      onClose();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Failed to fork build');
    }
  };

  const filteredBuilds = builds.filter(build => {
    if (!searchQuery) return true;
    const query = searchQuery.toLowerCase();
    return (
      build.name?.toLowerCase().includes(query) ||
      build.device_codename?.toLowerCase().includes(query) ||
      build.description?.toLowerCase().includes(query)
    );
  });

  if (!show) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm" onClick={onClose}>
      <motion.div 
        initial={{ opacity: 0, scale: 0.95 }} 
        animate={{ opacity: 1, scale: 1 }}
        onClick={(e) => e.stopPropagation()}
        className="glass-card rounded-2xl p-6 max-w-4xl w-full mx-4 max-h-[85vh] overflow-hidden flex flex-col">
        
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-2xl font-bold text-white flex items-center gap-2">
            <GitBranch className="w-7 h-7 text-[#E95420]" />
            Fork Previous Build
          </h2>
          <button onClick={onClose} className="text-white/50 hover:text-white">
            <XCircle className="w-6 h-6" />
          </button>
        </div>

        <p className="text-sm text-white/60 mb-4">
          Select a previous successful build to use as a template for your new build. This will copy all configurations and settings.
        </p>

        {/* Search */}
        <div className="relative mb-4">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-white/40" />
          <input
            type="text"
            placeholder="Search builds by name, device, or description..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2.5 rounded-lg bg-black/40 border border-white/10 text-white placeholder-white/30 focus:border-[#E95420]/50 focus:outline-none"
          />
        </div>

        {/* Builds List */}
        <div className="flex-1 overflow-y-auto space-y-2 mb-4">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-8 h-8 animate-spin text-[#E95420]" />
            </div>
          ) : filteredBuilds.length === 0 ? (
            <div className="text-center py-12">
              <GitBranch className="w-12 h-12 text-white/20 mx-auto mb-3" />
              <p className="text-sm text-white/50">No successful builds found</p>
              <p className="text-xs text-white/30 mt-1">
                {searchQuery ? 'Try a different search query' : 'Complete a build first to fork it later'}
              </p>
            </div>
          ) : (
            filteredBuilds.map((build) => (
              <motion.div
                key={build.build_id}
                whileHover={{ scale: 1.01 }}
                onClick={() => setSelectedBuild(build)}
                className={`p-4 rounded-lg cursor-pointer transition-all ${
                  selectedBuild?.build_id === build.build_id
                    ? 'bg-[#E95420]/20 border-2 border-[#E95420]/50'
                    : 'bg-black/20 border border-white/5 hover:border-white/20'
                }`}
              >
                <div className="flex items-start justify-between mb-2">
                  <div className="flex-1">
                    <h3 className="font-semibold text-white text-sm mb-1">
                      {build.name || `Build ${build.build_id.substring(0, 8)}`}
                    </h3>
                    {build.description && (
                      <p className="text-xs text-white/50 mb-2">{build.description}</p>
                    )}
                  </div>
                  {selectedBuild?.build_id === build.build_id && (
                    <CheckCircle2 className="w-5 h-5 text-[#E95420]" />
                  )}
                </div>

                <div className="flex flex-wrap gap-2 text-xs">
                  {build.device_codename && (
                    <div className="flex items-center gap-1 px-2 py-1 rounded bg-black/30 text-white/60">
                      <Smartphone className="w-3 h-3" />
                      {build.device_codename}
                    </div>
                  )}
                  {build.created_at && (
                    <div className="flex items-center gap-1 px-2 py-1 rounded bg-black/30 text-white/60">
                      <Calendar className="w-3 h-3" />
                      {new Date(build.created_at).toLocaleDateString()}
                    </div>
                  )}
                  {build.configuration?.preset_used && (
                    <div className="flex items-center gap-1 px-2 py-1 rounded bg-purple-500/20 text-purple-300">
                      Preset: {build.configuration.preset_used}
                    </div>
                  )}
                </div>

                {build.configuration && (
                  <div className="mt-2 pt-2 border-t border-white/5">
                    <p className="text-[10px] text-white/40 mb-1">Configuration highlights:</p>
                    <div className="flex flex-wrap gap-1">
                      {Object.entries(build.configuration).slice(0, 5).map(([key, value]) => (
                        <span key={key} className="text-[9px] px-1.5 py-0.5 rounded bg-white/5 text-white/50">
                          {key}: {String(value).substring(0, 15)}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </motion.div>
            ))
          )}
        </div>

        {/* Fork Button */}
        <button
          onClick={handleFork}
          disabled={!selectedBuild}
          className="w-full py-3 rounded-xl font-semibold flex items-center justify-center gap-2 bg-[#E95420] text-white hover:bg-[#E95420]/90 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <GitBranch className="w-5 h-5" />
          Fork Selected Build
        </button>
      </motion.div>
    </div>
  );
};

export default ForkBuildModal;
