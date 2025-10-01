import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, Upload, BookOpen, Zap, Shield, Brain, ArrowRight, Sparkles } from 'lucide-react';
import { motion } from 'framer-motion';
import toast from 'react-hot-toast';

const LandingPage = ({ onSearch, isLoading }) => {
  const [query, setQuery] = useState('');
  const [selectedFilters, setSelectedFilters] = useState([]);
  const [stats, setStats] = useState({ documents: 0, searchable: true });
  const navigate = useNavigate();

  const filterOptions = [
    { value: 'facts', label: 'Facts', color: 'bg-blue-100 text-blue-800' },
    { value: 'grounds', label: 'Legal Grounds', color: 'bg-green-100 text-green-800' },
    { value: 'prayers', label: 'Prayers', color: 'bg-purple-100 text-purple-800' },
    { value: 'judgment', label: 'Judgment', color: 'bg-orange-100 text-orange-800' }
  ];

  const exampleQueries = [
    "Constitutional validity of preventive detention",
    "Right to privacy and surveillance laws",
    "Contract breach and damages calculation",
    "Criminal procedure and bail conditions"
  ];

  useEffect(() => {
    // Fetch system stats
    fetchStats();
  }, []);

  const fetchStats = async () => {
    try {
      const response = await fetch('http://localhost:8000/health');
      const data = await response.json();
      setStats({
        documents: data.total_documents || 0,
        searchable: data.status === 'healthy'
      });
    } catch (error) {
      console.error('Error fetching stats:', error);
      setStats({ documents: 0, searchable: false });
    }
  };

  const handleSearch = async (e) => {
    e.preventDefault();
    
    if (!query.trim()) {
      toast.error('Please enter a search query');
      return;
    }

    if (stats.documents === 0) {
      toast.error('No documents available. Please upload some legal documents first.');
      return;
    }

    await onSearch(query, selectedFilters.length > 0 ? selectedFilters : null);
    navigate('/search');
  };

  const handleFilterToggle = (filter) => {
    setSelectedFilters(prev => 
      prev.includes(filter)
        ? prev.filter(f => f !== filter)
        : [...prev, filter]
    );
  };

  const handleExampleClick = (example) => {
    setQuery(example);
  };

  return (
    <div className="relative min-h-screen overflow-hidden">
      {/* Animated Background */}
      <div className="absolute inset-0">
        <motion.div
          className="absolute top-1/4 left-1/4 w-96 h-96 bg-blue-300/20 rounded-full blur-3xl"
          animate={{
            x: [0, 100, 0],
            y: [0, -100, 0],
          }}
          transition={{
            duration: 20,
            repeat: Infinity,
            ease: "linear"
          }}
        />
        <motion.div
          className="absolute bottom-1/4 right-1/4 w-80 h-80 bg-indigo-300/20 rounded-full blur-3xl"
          animate={{
            x: [0, -100, 0],
            y: [0, 100, 0],
          }}
          transition={{
            duration: 25,
            repeat: Infinity,
            ease: "linear"
          }}
        />
      </div>

      <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-20 pb-16">
        {/* Hero Section */}
        <div className="text-center mb-16">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
          >
            <div className="inline-flex items-center space-x-2 bg-gradient-to-r from-blue-100 to-indigo-100 rounded-full px-6 py-3 mb-8">
              <Sparkles className="h-5 w-5 text-blue-600" />
              <span className="text-blue-800 font-medium">AI-Powered Legal Research</span>
            </div>
            
            <h1 className="text-5xl md:text-7xl font-bold mb-6 bg-gradient-to-r from-blue-600 via-indigo-600 to-purple-600 bg-clip-text text-transparent leading-tight">
              Legal Judgment
              <br />
              Retrieval System
            </h1>
            
            <p className="text-xl md:text-2xl text-gray-600 mb-12 max-w-3xl mx-auto leading-relaxed">
              Harness the power of AI to search through legal precedents, analyze judgments, 
              and get intelligent insights from your legal document database.
            </p>
          </motion.div>

          {/* Search Section */}
          <motion.div
            initial={{ opacity: 0, y: 40 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.2 }}
            className="max-w-4xl mx-auto"
          >
            <form onSubmit={handleSearch} className="mb-8">
              <div className="relative group">
                <div className="absolute inset-0 bg-gradient-to-r from-blue-600 to-indigo-600 rounded-2xl blur opacity-75 group-hover:opacity-100 transition duration-300"></div>
                <div className="relative bg-white rounded-2xl p-2 shadow-2xl">
                  <div className="flex flex-col md:flex-row gap-4">
                    <div className="flex-1 relative">
                      <Search className="absolute left-4 top-1/2 transform -translate-y-1/2 text-gray-400 h-5 w-5" />
                      <input
                        type="text"
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                        placeholder="Enter your legal query... e.g., 'breach of contract remedies'"
                        className="w-full pl-12 pr-4 py-4 text-lg border-none outline-none rounded-xl focus:ring-2 focus:ring-blue-500 transition-all duration-200"
                        disabled={isLoading}
                      />
                    </div>
                    
                    <motion.button
                      type="submit"
                      disabled={isLoading || !query.trim()}
                      whileHover={{ scale: 1.02 }}
                      whileTap={{ scale: 0.98 }}
                      className={`px-8 py-4 rounded-xl font-semibold text-white transition-all duration-200 flex items-center space-x-2 ${
                        isLoading || !query.trim()
                          ? 'bg-gray-400 cursor-not-allowed'
                          : 'bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 shadow-lg hover:shadow-xl'
                      }`}
                    >
                      {isLoading ? (
                        <>
                          <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                          <span>Searching...</span>
                        </>
                      ) : (
                        <>
                          <Search className="h-5 w-5" />
                          <span>Search</span>
                        </>
                      )}
                    </motion.button>
                  </div>
                </div>
              </div>
            </form>

            {/* Filters */}
            <div className="flex flex-wrap justify-center gap-2 mb-8">
              <span className="text-sm font-medium text-gray-600 mr-2 self-center">Filter by section:</span>
              {filterOptions.map((filter) => (
                <motion.button
                  key={filter.value}
                  type="button"
                  onClick={() => handleFilterToggle(filter.value)}
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  className={`px-4 py-2 rounded-full text-sm font-medium transition-all duration-200 ${
                    selectedFilters.includes(filter.value)
                      ? 'bg-blue-600 text-white shadow-md'
                      : filter.color
                  }`}
                >
                  {filter.label}
                </motion.button>
              ))}
            </div>

            {/* Example Queries */}
            <div className="text-center">
              <p className="text-sm text-gray-600 mb-4">Try these example queries:</p>
              <div className="flex flex-wrap justify-center gap-2">
                {exampleQueries.map((example, index) => (
                  <motion.button
                    key={index}
                    onClick={() => handleExampleClick(example)}
                    whileHover={{ scale: 1.02 }}
                    className="px-4 py-2 bg-white/70 backdrop-blur-sm rounded-lg text-sm text-gray-700 hover:bg-white hover:shadow-md transition-all duration-200 border border-gray-200"
                  >
                    "{example}"
                  </motion.button>
                ))}
              </div>
            </div>
          </motion.div>
        </div>

        {/* Stats Section */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.4 }}
          className="grid grid-cols-1 md:grid-cols-3 gap-8 mb-20"
        >
          <div className="text-center p-8 bg-white/70 backdrop-blur-sm rounded-2xl shadow-lg border border-white/50">
            <div className="w-16 h-16 bg-gradient-to-r from-blue-500 to-blue-600 rounded-2xl flex items-center justify-center mx-auto mb-4">
              <BookOpen className="h-8 w-8 text-white" />
            </div>
            <h3 className="text-2xl font-bold text-gray-900 mb-2">{stats.documents.toLocaleString()}</h3>
            <p className="text-gray-600">Legal Documents</p>
          </div>

          <div className="text-center p-8 bg-white/70 backdrop-blur-sm rounded-2xl shadow-lg border border-white/50">
            <div className="w-16 h-16 bg-gradient-to-r from-indigo-500 to-indigo-600 rounded-2xl flex items-center justify-center mx-auto mb-4">
              <Brain className="h-8 w-8 text-white" />
            </div>
            <h3 className="text-2xl font-bold text-gray-900 mb-2">AI-Powered</h3>
            <p className="text-gray-600">Smart Analysis</p>
          </div>

          <div className="text-center p-8 bg-white/70 backdrop-blur-sm rounded-2xl shadow-lg border border-white/50">
            <div className="w-16 h-16 bg-gradient-to-r from-purple-500 to-purple-600 rounded-2xl flex items-center justify-center mx-auto mb-4">
              <Zap className="h-8 w-8 text-white" />
            </div>
            <h3 className="text-2xl font-bold text-gray-900 mb-2">Instant</h3>
            <p className="text-gray-600">Search Results</p>
          </div>
        </motion.div>

        {/* Features Section */}
        <motion.div
          initial={{ opacity: 0, y: 40 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.6 }}
          className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center mb-20"
        >
          <div>
            <h2 className="text-4xl font-bold text-gray-900 mb-6">
              Intelligent Legal Research
            </h2>
            <p className="text-lg text-gray-600 mb-8">
              Our AI system understands legal context, extracts relevant precedents, 
              and provides comprehensive analysis to support your research needs.
            </p>
            
            <div className="space-y-6">
              <div className="flex items-start space-x-4">
                <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center flex-shrink-0">
                  <Search className="h-5 w-5 text-blue-600" />
                </div>
                <div>
                  <h3 className="font-semibold text-gray-900 mb-1">Semantic Search</h3>
                  <p className="text-gray-600">Find relevant cases based on meaning, not just keywords</p>
                </div>
              </div>

              <div className="flex items-start space-x-4">
                <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center flex-shrink-0">
                  <Brain className="h-5 w-5 text-green-600" />
                </div>
                <div>
                  <h3 className="font-semibold text-gray-900 mb-1">AI Analysis</h3>
                  <p className="text-gray-600">Get intelligent summaries and legal reasoning</p>
                </div>
              </div>

              <div className="flex items-start space-x-4">
                <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center flex-shrink-0">
                  <Shield className="h-5 w-5 text-purple-600" />
                </div>
                <div>
                  <h3 className="font-semibold text-gray-900 mb-1">Secure & Private</h3>
                  <p className="text-gray-600">Your documents stay secure on your local system</p>
                </div>
              </div>
            </div>
          </div>

          <div className="relative">
            <motion.div
              animate={{ 
                rotateY: [0, 10, 0],
                rotateX: [0, -5, 0]
              }}
              transition={{ 
                duration: 6,
                repeat: Infinity,
                ease: "easeInOut"
              }}
              className="bg-gradient-to-br from-white to-blue-50 rounded-2xl shadow-2xl p-8 border border-blue-100"
            >
              <div className="space-y-4">
                <div className="h-4 bg-gradient-to-r from-blue-200 to-blue-300 rounded-full w-3/4"></div>
                <div className="h-4 bg-gradient-to-r from-indigo-200 to-indigo-300 rounded-full w-1/2"></div>
                <div className="h-4 bg-gradient-to-r from-purple-200 to-purple-300 rounded-full w-2/3"></div>
                <div className="mt-6 space-y-2">
                  <div className="h-3 bg-gray-200 rounded w-full"></div>
                  <div className="h-3 bg-gray-200 rounded w-5/6"></div>
                  <div className="h-3 bg-gray-200 rounded w-4/5"></div>
                </div>
              </div>
            </motion.div>
          </div>
        </motion.div>

        {/* CTA Section */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.8 }}
          className="text-center bg-gradient-to-r from-blue-600 to-indigo-600 rounded-3xl p-12 text-white"
        >
          <h2 className="text-3xl font-bold mb-4">Ready to Get Started?</h2>
          <p className="text-xl mb-8 text-blue-100">
            Upload your legal documents and start searching with AI-powered insights
          </p>
          
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <motion.button
              onClick={() => navigate('/upload')}
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              className="px-8 py-4 bg-white text-blue-600 rounded-xl font-semibold hover:shadow-lg transition-all duration-200 flex items-center justify-center space-x-2"
            >
              <Upload className="h-5 w-5" />
              <span>Upload Documents</span>
            </motion.button>
            
            <motion.button
              onClick={() => setQuery("constitutional validity of laws")}
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              className="px-8 py-4 bg-transparent border-2 border-white text-white rounded-xl font-semibold hover:bg-white hover:text-blue-600 transition-all duration-200 flex items-center justify-center space-x-2"
            >
              <span>Try Demo Search</span>
              <ArrowRight className="h-5 w-5" />
            </motion.button>
          </div>
        </motion.div>
      </div>
    </div>
  );
};

export default LandingPage;