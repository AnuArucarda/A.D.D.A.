import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Upload, Download, Link, Smartphone, Cpu, HardDrive, Package, 
  FileArchive, Loader2, CheckCircle2, XCircle, AlertCircle, Info,
  ExternalLink, Zap, GitBranch, Search, Play
} from 'lucide-react';
import axios from 'axios';
import { toast } from 'sonner';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const FactoryImageModal = ({ show, onClose, deviceInfo, onImagesExtracted }) => {
  const [activeTab, setActiveTab] = useState('auto'); // auto, upload, link
  const [manufacturers, setManufacturers] = useState({});
  const [uploadedImages, setUploadedImages] = useState({});
  const [loading, setLoading] = useState(false);
  const [extracting, setExtracting] = useState(false);
  const [downloadUrl, setDownloadUrl] = useState('');
  const [selectedFile, setSelectedFile] = useState(null);
  const [extractedData, setExtractedData] = useState(null);
  const [autoDetectResult, setAutoDetectResult] = useState(null);

  useEffect(() => {
    if (show) {
      fetchManufacturers();
      fetchUploadedImages();
    }
  }, [show]);

  const fetchManufacturers = async () => {
    try {
      const res = await axios.get(`${API}/factory-images/manufacturers`);
      setManufacturers(res.data.manufacturers || {});
    } catch (e) {
      console.error('Failed to fetch manufacturers:', e);
    }
  };

  const fetchUploadedImages = async () => {
    try {
      const res = await axios.get(`${API}/factory-images/uploaded`);
      setUploadedImages(res.data.images || {});
    } catch (e) {
      console.error('Failed to fetch uploaded images:', e);
    }
  };

  const handleAutoDetect = async () => {
    if (!deviceInfo) {
      toast.error('No device connected');
      return;
    }

    setLoading(true);
    try {
      const res = await axios.post(`${API}/factory-images/auto-detect`, {
        device_info: deviceInfo
      });

      if (res.data.error) {
        setAutoDetectResult({ error: res.data.error });
        toast.error(res.data.error);
      } else {
        setAutoDetectResult(res.data);
        toast.success('Factory images detected and downloaded!');
        await fetchUploadedImages();
      }
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Auto-detection failed');
    } finally {
      setLoading(false);
    }
  };

  const handleDownloadFromUrl = async () => {
    if (!downloadUrl) {
      toast.error('Please enter a download URL');
      return;
    }

    const codename = deviceInfo?.codename || 'unknown';
    setLoading(true);
    try {
      const res = await axios.post(`${API}/factory-images/download`, {
        url: downloadUrl,
        device_codename: codename,
        manufacturer: deviceInfo?.manufacturer
      });

      toast.success('Factory images downloaded successfully!');
      setDownloadUrl('');
      await fetchUploadedImages();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Download failed');
    } finally {
      setLoading(false);
    }
  };

  const handleFileSelect = (e) => {
    const file = e.target.files[0];
    if (file) {
      setSelectedFile(file);
      toast.success(`Selected: ${file.name}`);
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) {
      toast.error('Please select a file');
      return;
    }

    // In a real implementation, you'd upload the file to the server first
    // For now, we'll assume the file is already accessible on the server
    toast.info('File upload would happen here. For demo, using local path.');
  };

  const handleExtract = async (deviceCodename) => {
    setExtracting(true);
    try {
      const res = await axios.post(`${API}/factory-images/${deviceCodename}/extract`);
      setExtractedData(res.data);
      
      if (onImagesExtracted) {
        onImagesExtracted(res.data);
      }
      
      toast.success('Factory images extracted successfully!');
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Extraction failed');
    } finally {
      setExtracting(false);
    }
  };

  if (!show) return null;

  const deviceManufacturer = deviceInfo?.manufacturer?.toLowerCase();
  const manufacturerInfo = manufacturers[deviceManufacturer];

  return (
    <div className=\"fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm\" onClick={onClose}>
      <motion.div 
        initial={{ opacity: 0, scale: 0.95 }} 
        animate={{ opacity: 1, scale: 1 }}
        onClick={(e) => e.stopPropagation()}
        className=\"glass-card rounded-2xl p-6 max-w-5xl w-full mx-4 max-h-[90vh] overflow-y-auto\">
        
        <div className=\"flex items-center justify-between mb-6\">
          <div>
            <h2 className=\"text-2xl font-bold text-white flex items-center gap-2\">
              <Package className=\"w-7 h-7 text-[#E95420]\" />
              Factory Image Manager
            </h2>
            {deviceInfo && (
              <p className=\"text-sm text-white/60 mt-1\">
                {deviceInfo.manufacturer} {deviceInfo.model} ({deviceInfo.codename})
              </p>
            )}
          </div>
          <button onClick={onClose} className=\"text-white/50 hover:text-white\">
            <XCircle className=\"w-6 h-6\" />
          </button>
        </div>

        <p className=\"text-sm text-white/60 mb-6\">
          Factory images contain all the official firmware files for your device. Upload your own, 
          provide a download link, or let the app automatically detect and download them for you.
        </p>

        {/* Tabs */}
        <div className=\"flex gap-2 mb-6\">
          <button
            onClick={() => setActiveTab('auto')}
            className={`flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-all ${
              activeTab === 'auto'
                ? 'bg-[#E95420]/20 text-[#E95420] border border-[#E95420]/30'
                : 'text-white/60 hover:text-white hover:bg-white/5'
            }`}
          >
            <Zap className=\"w-4 h-4\" />
            Auto-Detect
          </button>
          <button
            onClick={() => setActiveTab('link')}
            className={`flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-all ${
              activeTab === 'link'
                ? 'bg-[#E95420]/20 text-[#E95420] border border-[#E95420]/30'
                : 'text-white/60 hover:text-white hover:bg-white/5'
            }`}
          >
            <Link className=\"w-4 h-4\" />
            From URL
          </button>
          <button
            onClick={() => setActiveTab('upload')}
            className={`flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-all ${
              activeTab === 'upload'
                ? 'bg-[#E95420]/20 text-[#E95420] border border-[#E95420]/30'
                : 'text-white/60 hover:text-white hover:bg-white/5'
            }`}
          >
            <Upload className=\"w-4 h-4\" />
            Upload File
          </button>
        </div>

        {/* Tab Content */}
        <div className=\"space-y-6\">
          {/* Auto-Detect Tab */}
          {activeTab === 'auto' && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className=\"space-y-4\"
            >
              <div className=\"p-4 bg-gradient-to-r from-[#E95420]/10 to-purple-500/10 border border-[#E95420]/30 rounded-xl\">
                <div className=\"flex items-start gap-3 mb-3\">
                  <Zap className=\"w-5 h-5 text-[#E95420] mt-0.5\" />
                  <div className=\"flex-1\">
                    <h3 className=\"font-semibold text-white mb-1\">Automatic Detection</h3>
                    <p className=\"text-sm text-white/60\">
                      The app will automatically identify your device and download the correct factory images 
                      from the manufacturer's official source.
                    </p>
                  </div>
                </div>

                {manufacturerInfo && (
                  <div className=\"p-3 bg-black/30 rounded-lg mb-3\">
                    <p className=\"text-xs text-white/50 mb-1\">Manufacturer Source</p>
                    <p className=\"text-sm text-white font-medium\">{manufacturerInfo.name}</p>
                    <a 
                      href={manufacturerInfo.base_url} 
                      target=\"_blank\" 
                      rel=\"noopener noreferrer\"
                      className=\"text-xs text-[#E95420] hover:text-[#E95420]/80 inline-flex items-center gap-1 mt-1\"
                    >
                      <ExternalLink className=\"w-3 h-3\" />
                      {manufacturerInfo.base_url}
                    </a>
                    {manufacturerInfo.note && (
                      <p className=\"text-xs text-yellow-400 mt-2 flex items-center gap-1\">
                        <Info className=\"w-3 h-3\" />
                        {manufacturerInfo.note}
                      </p>
                    )}
                  </div>
                )}

                <button
                  onClick={handleAutoDetect}
                  disabled={loading || !deviceInfo}
                  className=\"w-full py-3 rounded-xl font-semibold flex items-center justify-center gap-2 bg-[#E95420] text-white hover:bg-[#E95420]/90 transition-all disabled:opacity-50 disabled:cursor-not-allowed\"
                >
                  {loading ? (
                    <><Loader2 className=\"w-5 h-5 animate-spin\" /> Detecting & Downloading...</>
                  ) : (
                    <><Play className=\"w-5 h-5\" /> Auto-Detect & Download</>
                  )}
                </button>
              </div>

              {autoDetectResult && (
                <div className={`p-4 rounded-xl border ${
                  autoDetectResult.error 
                    ? 'bg-red-500/10 border-red-500/30' 
                    : 'bg-green-500/10 border-green-500/30'
                }`}>
                  {autoDetectResult.error ? (
                    <>
                      <AlertCircle className=\"w-5 h-5 text-red-400 mb-2\" />
                      <p className=\"text-sm text-red-300\">{autoDetectResult.error}</p>
                    </>
                  ) : (
                    <>
                      <CheckCircle2 className=\"w-5 h-5 text-green-400 mb-2\" />
                      <p className=\"text-sm text-green-300\">Factory images downloaded successfully!</p>
                      <p className=\"text-xs text-white/50 mt-1\">{autoDetectResult.filename}</p>
                    </>
                  )}
                </div>
              )}
            </motion.div>
          )}

          {/* Link Tab */}
          {activeTab === 'link' && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className=\"space-y-4\"
            >
              <div className=\"p-4 bg-blue-500/10 border border-blue-500/30 rounded-xl\">
                <div className=\"flex items-start gap-3 mb-3\">
                  <Link className=\"w-5 h-5 text-blue-400 mt-0.5\" />
                  <div>
                    <h3 className=\"font-semibold text-white mb-1\">Download from URL</h3>
                    <p className=\"text-sm text-white/60\">
                      Provide a direct link to your device's factory images. Works with Google, Samsung, OnePlus, and more.
                    </p>
                  </div>
                </div>

                <div className=\"space-y-3\">
                  <input
                    type=\"text\"
                    value={downloadUrl}
                    onChange={(e) => setDownloadUrl(e.target.value)}
                    placeholder=\"https://example.com/factory-images.zip\"
                    className=\"w-full px-4 py-3 rounded-lg bg-black/40 border border-white/10 text-white placeholder-white/30 focus:border-[#E95420]/50 focus:outline-none\"
                  />

                  <button
                    onClick={handleDownloadFromUrl}
                    disabled={loading || !downloadUrl}
                    className=\"w-full py-3 rounded-xl font-semibold flex items-center justify-center gap-2 bg-[#E95420] text-white hover:bg-[#E95420]/90 transition-all disabled:opacity-50 disabled:cursor-not-allowed\"
                  >
                    {loading ? (
                      <><Loader2 className=\"w-5 h-5 animate-spin\" /> Downloading...</>
                    ) : (
                      <><Download className=\"w-5 h-5\" /> Download Factory Images</>
                    )}
                  </button>
                </div>

                <div className=\"mt-4 p-3 bg-black/20 rounded-lg\">
                  <p className=\"text-xs text-white/50 mb-2\">📌 Example URLs:</p>
                  <div className=\"space-y-1 text-xs text-white/40\">
                    <p>• Google: https://developers.google.com/android/images</p>
                    <p>• Samsung: https://samfw.com</p>
                    <p>• OnePlus: https://www.oneplus.com/support/softwareupgrade</p>
                  </div>
                </div>
              </div>
            </motion.div>
          )}

          {/* Upload Tab */}
          {activeTab === 'upload' && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className=\"space-y-4\"
            >
              <div className=\"p-4 bg-purple-500/10 border border-purple-500/30 rounded-xl\">
                <div className=\"flex items-start gap-3 mb-3\">
                  <Upload className=\"w-5 h-5 text-purple-400 mt-0.5\" />
                  <div>
                    <h3 className=\"font-semibold text-white mb-1\">Upload Local File</h3>
                    <p className=\"text-sm text-white/60\">
                      Upload factory images you've already downloaded. Supports .zip, .tar, .tar.gz formats.
                    </p>
                  </div>
                </div>

                <label className=\"block w-full cursor-pointer\">
                  <div className=\"border-2 border-dashed border-white/20 rounded-xl p-8 text-center hover:border-[#E95420]/50 transition-all\">
                    <FileArchive className=\"w-12 h-12 text-white/40 mx-auto mb-3\" />
                    {selectedFile ? (
                      <div>
                        <p className=\"text-white font-medium\">{selectedFile.name}</p>
                        <p className=\"text-sm text-white/50 mt-1\">
                          {(selectedFile.size / (1024 * 1024)).toFixed(2)} MB
                        </p>
                      </div>
                    ) : (
                      <div>
                        <p className=\"text-white mb-1\">Click to select or drag & drop</p>
                        <p className=\"text-sm text-white/50\">ZIP, TAR, TAR.GZ files accepted</p>
                      </div>
                    )}
                  </div>
                  <input 
                    type=\"file\" 
                    accept=\".zip,.tar,.tar.gz,.tgz\"
                    onChange={handleFileSelect}
                    className=\"hidden\" 
                  />
                </label>

                {selectedFile && (
                  <button
                    onClick={handleUpload}
                    disabled={loading}
                    className=\"w-full mt-4 py-3 rounded-xl font-semibold flex items-center justify-center gap-2 bg-[#E95420] text-white hover:bg-[#E95420]/90 transition-all disabled:opacity-50 disabled:cursor-not-allowed\"
                  >
                    {loading ? (
                      <><Loader2 className=\"w-5 h-5 animate-spin\" /> Uploading...</>
                    ) : (
                      <><Upload className=\"w-5 h-5\" /> Upload Factory Images</>
                    )}
                  </button>
                )}
              </div>
            </motion.div>
          )}

          {/* Uploaded Images List */}
          {Object.keys(uploadedImages).length > 0 && (
            <div className=\"mt-6\">
              <h3 className=\"text-lg font-semibold text-white mb-3 flex items-center gap-2\">
                <FileArchive className=\"w-5 h-5 text-[#E95420]\" />
                Uploaded Images
              </h3>
              <div className=\"space-y-2\">
                {Object.entries(uploadedImages).map(([codename, imageInfo]) => (
                  <div key={codename} className=\"p-4 bg-black/20 border border-white/5 rounded-xl\">
                    <div className=\"flex items-start justify-between mb-2\">
                      <div className=\"flex-1\">
                        <h4 className=\"font-semibold text-white text-sm\">{imageInfo.filename}</h4>
                        <p className=\"text-xs text-white/50\">Device: {codename}</p>
                        <p className=\"text-xs text-white/40\">
                          Size: {(imageInfo.size / (1024 * 1024)).toFixed(2)} MB
                        </p>
                      </div>
                      <button
                        onClick={() => handleExtract(codename)}
                        disabled={extracting}
                        className=\"px-3 py-1.5 rounded-lg text-xs font-medium bg-[#E95420]/20 text-[#E95420] hover:bg-[#E95420]/30 transition-all flex items-center gap-1\"
                      >
                        {extracting ? (
                          <><Loader2 className=\"w-3 h-3 animate-spin\" /> Extracting...</>
                        ) : (
                          <><Package className=\"w-3 h-3\" /> Extract</>
                        )}
                      </button>
                    </div>

                    {imageInfo.metadata && Object.keys(imageInfo.metadata).length > 0 && (
                      <div className=\"mt-2 pt-2 border-t border-white/5\">
                        <p className=\"text-[10px] text-white/40 mb-1\">Metadata:</p>
                        <div className=\"flex flex-wrap gap-1\">
                          {Object.entries(imageInfo.metadata).map(([key, value]) => (
                            <span key={key} className=\"text-[9px] px-1.5 py-0.5 rounded bg-white/5 text-white/50\">
                              {key}: {String(value)}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Extracted Data */}
          {extractedData && (
            <div className=\"mt-6 p-4 bg-green-500/10 border border-green-500/30 rounded-xl\">
              <h3 className=\"text-lg font-semibold text-green-300 mb-3 flex items-center gap-2\">
                <CheckCircle2 className=\"w-5 h-5\" />
                Extraction Complete!
              </h3>
              <div className=\"grid grid-cols-2 gap-3\">
                {extractedData.analysis?.boot_image && (
                  <div className=\"p-2 bg-black/30 rounded-lg\">
                    <p className=\"text-xs text-white/50\">Boot Image</p>
                    <p className=\"text-sm text-white truncate\">✓ Found</p>
                  </div>
                )}
                {extractedData.analysis?.system_image && (
                  <div className=\"p-2 bg-black/30 rounded-lg\">
                    <p className=\"text-xs text-white/50\">System Image</p>
                    <p className=\"text-sm text-white truncate\">✓ Found</p>
                  </div>
                )}
                {extractedData.analysis?.vendor_image && (
                  <div className=\"p-2 bg-black/30 rounded-lg\">
                    <p className=\"text-xs text-white/50\">Vendor Image</p>
                    <p className=\"text-sm text-white truncate\">✓ Found</p>
                  </div>
                )}
                {extractedData.analysis?.kernel_image && (
                  <div className=\"p-2 bg-black/30 rounded-lg\">
                    <p className=\"text-xs text-white/50\">Kernel Image</p>
                    <p className=\"text-sm text-white truncate\">✓ Found</p>
                  </div>
                )}
              </div>
              <p className=\"text-xs text-white/50 mt-3\">
                Extracted {extractedData.extracted_files?.length || 0} files
              </p>
            </div>
          )}
        </div>
      </motion.div>
    </div>
  );
};

export default FactoryImageModal;
