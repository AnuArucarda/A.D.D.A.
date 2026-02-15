import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { 
  Github, Upload, Download, Search, GitFork, Star, ExternalLink, 
  XCircle, CheckCircle2, Loader2, Clock, Users, Code, Lock, Globe
} from 'lucide-react';
import axios from 'axios';
import { toast } from 'sonner';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const GitHubIntegrationModal = ({ show, onClose, buildData, onRecipeImported }) => {
  const [activeTab, setActiveTab] = useState('save'); // save, import, browse
  const [githubToken, setGithubToken] = useState('');
  const [tokenConfigured, setTokenConfigured] = useState(false);
  const [userRepos, setUserRepos] = useState([]);
  const [selectedRepo, setSelectedRepo] = useState('');
  const [recipeName, setRecipeName] = useState('');
  const [importUrl, setImportUrl] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [userId] = useState('user_001'); // In production, get from auth

  useEffect(() => {
    if (show && tokenConfigured) {
      fetchUserRepos();
    }
  }, [show, tokenConfigured]);

  const configureToken = async () => {
    if (!githubToken) {
      toast.error('Please enter your GitHub token');
      return;
    }

    setLoading(true);
    try {
      await axios.post(`${API}/github/set-token`, {
        user_id: userId,
        github_token: githubToken
      });
      
      setTokenConfigured(true);
      toast.success('GitHub token configured successfully!');
      fetchUserRepos();
    } catch (e) {
      toast.error('Failed to configure GitHub token');
    } finally {
      setLoading(false);
    }
  };

  const fetchUserRepos = async () => {
    try {
      const res = await axios.get(`${API}/github/user-repos`, {
        params: { user_id: userId, recipe_repos_only: true }
      });
      setUserRepos(res.data.repositories || []);
    } catch (e) {
      console.error('Failed to fetch repositories:', e);
    }
  };

  const createNewRepo = async () => {
    const repoName = prompt('Enter repository name:', 'adda-recipes');
    if (!repoName) return;

    setLoading(true);
    try {
      const res = await axios.post(`${API}/github/create-repo`, {
        user_id: userId,
        repo_name: repoName,
        description: 'A.D.D.A. Build Recipes',
        is_private: false
      });

      if (res.data.error) {
        toast.error(res.data.error);
      } else {
        toast.success('Repository created!');
        fetchUserRepos();
      }
    } catch (e) {
      toast.error('Failed to create repository');
    } finally {
      setLoading(false);
    }
  };

  const saveRecipeToGitHub = async () => {
    if (!selectedRepo || !recipeName) {
      toast.error('Please select a repository and enter recipe name');
      return;
    }

    setLoading(true);
    try {
      const [owner, repo] = selectedRepo.split('/');
      
      const res = await axios.post(`${API}/github/save-recipe`, {
        user_id: userId,
        repo_owner: owner,
        repo_name: repo,
        recipe_name: recipeName,
        recipe_data: buildData
      });

      if (res.data.success) {
        toast.success('Recipe saved to GitHub!');
        if (res.data.file_url) {
          window.open(res.data.file_url, '_blank');
        }
      } else {
        toast.error(res.data.error || 'Failed to save recipe');
      }
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Failed to save recipe');
    } finally {
      setLoading(false);
    }
  };

  const importRecipeFromUrl = async () => {
    if (!importUrl) {
      toast.error('Please enter a GitHub URL');
      return;
    }

    setLoading(true);
    try {
      const res = await axios.get(`${API}/github/load-recipe`, {
        params: { github_url: importUrl, user_id: userId }
      });

      if (res.data.error) {
        toast.error(res.data.error);
      } else {
        toast.success('Recipe imported successfully!');
        if (onRecipeImported) {
          onRecipeImported(res.data);
        }
        onClose();
      }
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Failed to import recipe');
    } finally {
      setLoading(false);
    }
  };

  const searchCommunityRecipes = async () => {
    if (!searchQuery) {
      toast.error('Please enter a search query');
      return;
    }

    setLoading(true);
    try {
      const res = await axios.get(`${API}/github/search-recipes`, {
        params: {
          query: searchQuery,
          build_type: buildData?.type,
          limit: 30
        }
      });

      setSearchResults(res.data.recipes || []);
      if (res.data.recipes.length === 0) {
        toast.info('No recipes found');
      }
    } catch (e) {
      toast.error('Search failed');
    } finally {
      setLoading(false);
    }
  };

  const forkRepository = async (repoFullName) => {
    const [owner, repo] = repoFullName.split('/');
    
    setLoading(true);
    try {
      const res = await axios.post(`${API}/github/fork-repo`, {
        user_id: userId,
        repo_owner: owner,
        repo_name: repo
      });

      if (res.data.error) {
        toast.error(res.data.error);
      } else {
        toast.success('Repository forked to your account!');
        fetchUserRepos();
      }
    } catch (e) {
      toast.error('Failed to fork repository');
    } finally {
      setLoading(false);
    }
  };

  if (!show) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm" onClick={onClose}>
      <motion.div 
        initial={{ opacity: 0, scale: 0.95 }} 
        animate={{ opacity: 1, scale: 1 }}
        onClick={(e) => e.stopPropagation()}
        className="glass-card rounded-2xl p-6 max-w-5xl w-full mx-4 max-h-[90vh] overflow-y-auto">
        
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-bold text-white flex items-center gap-2">
            <Github className="w-7 h-7 text-white" />
            GitHub Integration
          </h2>
          <button onClick={onClose} className="text-white/50 hover:text-white">
            <XCircle className="w-6 h-6" />
          </button>
        </div>

        {/* GitHub Token Configuration */}
        {!tokenConfigured && (
          <div className="mb-6 p-4 bg-blue-500/10 border border-blue-500/30 rounded-xl">
            <h3 className="font-semibold text-white mb-2 flex items-center gap-2">
              <Lock className="w-4 h-4" />
              Configure GitHub Access
            </h3>
            <p className="text-sm text-white/60 mb-3">
              Enter your GitHub Personal Access Token to save and fork recipes.
            </p>
            <div className="flex gap-2">
              <input
                type="password"
                value={githubToken}
                onChange={(e) => setGithubToken(e.target.value)}
                placeholder="ghp_xxxxxxxxxxxxxxxxxxxx"
                className="flex-1 px-4 py-2.5 rounded-lg bg-black/40 border border-white/10 text-white placeholder-white/30 focus:border-blue-500/50 focus:outline-none"
              />
              <button
                onClick={configureToken}
                disabled={loading}
                className="px-4 py-2.5 rounded-lg font-semibold bg-blue-500 text-white hover:bg-blue-600 transition-all disabled:opacity-50"
              >
                {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : 'Configure'}
              </button>
            </div>
            <a
              href="https://github.com/settings/tokens"
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs text-blue-400 hover:text-blue-300 mt-2 inline-flex items-center gap-1"
            >
              <ExternalLink className="w-3 h-3" />
              Get a GitHub token
            </a>
          </div>
        )}

        {/* Tabs */}
        <div className="flex gap-2 mb-6">
          <button
            onClick={() => setActiveTab('save')}
            className={`flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-all ${
              activeTab === 'save'
                ? 'bg-[#E95420]/20 text-[#E95420] border border-[#E95420]/30'
                : 'text-white/60 hover:text-white hover:bg-white/5'
            }`}
          >
            <Upload className="w-4 h-4" />
            Save to GitHub
          </button>
          <button
            onClick={() => setActiveTab('import')}
            className={`flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-all ${
              activeTab === 'import'
                ? 'bg-[#E95420]/20 text-[#E95420] border border-[#E95420]/30'
                : 'text-white/60 hover:text-white hover:bg-white/5'
            }`}
          >
            <Download className="w-4 h-4" />
            Import from URL
          </button>
          <button
            onClick={() => setActiveTab('browse')}
            className={`flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-all ${
              activeTab === 'browse'
                ? 'bg-[#E95420]/20 text-[#E95420] border border-[#E95420]/30'
                : 'text-white/60 hover:text-white hover:bg-white/5'
            }`}
          >
            <Globe className="w-4 h-4" />
            Browse Community
          </button>
        </div>

        {/* Tab Content */}
        {activeTab === 'save' && (
          <div className="space-y-4">
            <div className="flex gap-2 mb-4">
              <select
                value={selectedRepo}
                onChange={(e) => setSelectedRepo(e.target.value)}
                className="flex-1 px-4 py-2.5 rounded-lg bg-black/40 border border-white/10 text-white focus:border-[#E95420]/50 focus:outline-none"
                disabled={!tokenConfigured}
              >
                <option value="">Select Repository</option>
                {userRepos.map(repo => (
                  <option key={repo.full_name} value={repo.full_name}>
                    {repo.full_name}
                  </option>
                ))}
              </select>
              <button
                onClick={createNewRepo}
                disabled={!tokenConfigured || loading}
                className="px-4 py-2.5 rounded-lg font-semibold bg-green-500 text-white hover:bg-green-600 transition-all disabled:opacity-50"
              >
                + New Repo
              </button>
            </div>

            <input
              type="text"
              value={recipeName}
              onChange={(e) => setRecipeName(e.target.value)}
              placeholder="Recipe name (e.g., pixel8-gaming-kernel)"
              className="w-full px-4 py-2.5 rounded-lg bg-black/40 border border-white/10 text-white placeholder-white/30 focus:border-[#E95420]/50 focus:outline-none"
              disabled={!tokenConfigured}
            />

            <button
              onClick={saveRecipeToGitHub}
              disabled={!tokenConfigured || loading || !selectedRepo || !recipeName}
              className="w-full py-3 rounded-xl font-semibold flex items-center justify-center gap-2 bg-[#E95420] text-white hover:bg-[#E95420]/90 transition-all disabled:opacity-50"
            >
              {loading ? (
                <><Loader2 className="w-5 h-5 animate-spin" /> Saving...</>
              ) : (
                <><Upload className="w-5 h-5" /> Save Recipe to GitHub</>
              )}
            </button>
          </div>
        )}

        {activeTab === 'import' && (
          <div className="space-y-4">
            <input
              type="text"
              value={importUrl}
              onChange={(e) => setImportUrl(e.target.value)}
              placeholder="https://github.com/username/repo/blob/main/recipes/..."
              className="w-full px-4 py-2.5 rounded-lg bg-black/40 border border-white/10 text-white placeholder-white/30 focus:border-[#E95420]/50 focus:outline-none"
            />

            <button
              onClick={importRecipeFromUrl}
              disabled={loading || !importUrl}
              className="w-full py-3 rounded-xl font-semibold flex items-center justify-center gap-2 bg-[#E95420] text-white hover:bg-[#E95420]/90 transition-all disabled:opacity-50"
            >
              {loading ? (
                <><Loader2 className="w-5 h-5 animate-spin" /> Importing...</>
              ) : (
                <><Download className="w-5 h-5" /> Import Recipe</>
              )}
            </button>
          </div>
        )}

        {activeTab === 'browse' && (
          <div className="space-y-4">
            <div className="flex gap-2">
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && searchCommunityRecipes()}
                placeholder="Search community recipes..."
                className="flex-1 px-4 py-2.5 rounded-lg bg-black/40 border border-white/10 text-white placeholder-white/30 focus:border-[#E95420]/50 focus:outline-none"
              />
              <button
                onClick={searchCommunityRecipes}
                disabled={loading}
                className="px-4 py-2.5 rounded-lg font-semibold bg-[#E95420] text-white hover:bg-[#E95420]/90 transition-all"
              >
                <Search className="w-5 h-5" />
              </button>
            </div>

            {loading ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="w-8 h-8 animate-spin text-[#E95420]" />
              </div>
            ) : searchResults.length > 0 ? (
              <div className="space-y-2 max-h-96 overflow-y-auto">
                {searchResults.map((recipe, idx) => (
                  <div key={idx} className="p-4 bg-black/20 border border-white/5 rounded-xl hover:border-white/20 transition-all">
                    <div className="flex items-start justify-between mb-2">
                      <div className="flex-1">
                        <h4 className="font-semibold text-white text-sm">{recipe.name}</h4>
                        <p className="text-xs text-white/50">{recipe.repository}</p>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="flex items-center gap-1 text-xs text-yellow-400">
                          <Star className="w-3 h-3" /> {recipe.stars}
                        </span>
                      </div>
                    </div>
                    {recipe.description && (
                      <p className="text-xs text-white/60 mb-2">{recipe.description}</p>
                    )}
                    <div className="flex gap-2">
                      <button
                        onClick={() => window.open(recipe.url, '_blank')}
                        className="flex-1 px-3 py-1.5 rounded-lg text-xs font-medium bg-white/5 text-white hover:bg-white/10 transition-all flex items-center justify-center gap-1"
                      >
                        <ExternalLink className="w-3 h-3" /> View
                      </button>
                      {tokenConfigured && (
                        <button
                          onClick={() => forkRepository(recipe.repository)}
                          className="flex-1 px-3 py-1.5 rounded-lg text-xs font-medium bg-[#E95420]/20 text-[#E95420] hover:bg-[#E95420]/30 transition-all flex items-center justify-center gap-1"
                        >
                          <GitFork className="w-3 h-3" /> Fork
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-12 text-white/50">
                <Search className="w-12 h-12 mx-auto mb-3 opacity-20" />
                <p className="text-sm">Search for community recipes</p>
              </div>
            )}
          </div>
        )}
      </motion.div>
    </div>
  );
};

export default GitHubIntegrationModal;
