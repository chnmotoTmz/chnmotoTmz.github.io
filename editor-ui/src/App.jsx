import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Settings, PenSquare, Eye, FileText, Upload, Save, CheckCircle, AlertCircle, RefreshCw, Layout, Paintbrush, Loader2, Link as LinkIcon, Sparkles, ChevronDown, Plus, Globe, Search, Youtube, ImageIcon, ChevronRight, BookOpen, EyeOff, X, Copy, ClipboardCheck, Wrench, Menu, Send } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { getBlogs, getPosts, savePost, uploadImage, improvePost, optimizeAllPost, runToolAffiliate, runToolFactCheck, searchAcrossBlogs, generateThumbnail } from './api';

const App = () => {
  const [blogs, setBlogs] = useState({});
  const [selectedBlogId, setSelectedBlogId] = useState('');
  const [posts, setPosts] = useState([]);
  const [selectedPost, setSelectedPost] = useState(null);

  // Create / Edit states
  const [title, setTitle] = useState('');
  const [content, setContent] = useState('');
  const [isDraft, setIsDraft] = useState(true);
  const [editLink, setEditLink] = useState('');

  // UI states
  const [loading, setLoading] = useState(true);
  const [postsLoading, setPostsLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [improving, setImproving] = useState(false);
  const [optimizing, setOptimizing] = useState(false);
  const [runningTool, setRunningTool] = useState(false); // Kept from original
  const [showToolMenu, setShowToolMenu] = useState(false); // Kept from original
  const [status, setStatus] = useState({ message: '', type: '' });
  const [showPostPanel, setShowPostPanel] = useState(false);
  const [activeTab, setActiveTab] = useState('write'); // 'write' or 'preview'
  const [showImproveMenu, setShowImproveMenu] = useState(false);
  const [showCustomPrompt, setShowCustomPrompt] = useState(false);
  const [customPrompt, setCustomPrompt] = useState('');
  const [batchMode, setBatchMode] = useState(false);
  const [batchSelected, setBatchSelected] = useState([]);
  const [batchProgress, setBatchProgress] = useState('');
  const [uploading, setUploading] = useState(false); // Kept from original

  // Search states
  const [showSearchPanel, setShowSearchPanel] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [isSearching, setIsSearching] = useState(false);

  const fileInputRef = useRef(null);

  useEffect(() => {
    fetchBlogs();
  }, []);

  useEffect(() => {
    if (selectedBlogId) {
      fetchPosts(selectedBlogId);
      // Reset editor when switching blog
      setSelectedPost(null);
      setTitle('');
      setContent('');
    }
  }, [selectedBlogId]);

  const fetchBlogs = async () => {
    try {
      const data = await getBlogs();
      setBlogs(data);
      if (Object.keys(data).length > 0) {
        setSelectedBlogId(Object.keys(data)[0]);
      }
    } catch (error) {
      showStatus('ブログ一覧の読み込みに失敗しました', 'error');
    } finally {
      setLoading(false);
    }
  };

  const fetchPosts = async (blogId) => {
    setPostsLoading(true);
    try {
      const data = await getPosts(blogId);
      setPosts(data.posts || []);
    } catch (error) {
      showStatus('記事一覧の読み込みに失敗しました', 'error');
      setPosts([]);
    } finally {
      setPostsLoading(false);
    }
  };

  const [copied, setCopied] = useState(false);

  const showStatus = (message, type) => {
    setStatus({ message, type });
    setTimeout(() => setStatus({ message: '', type: '' }), 4000);
  };

  const IMPROVE_PRESETS = [
    { id: 'structure', label: '🏗️ 構造・動線整理', desc: '回遊率UP・目次整理・CTA追加' },
    { id: 'monetize', label: '💰 マネタイズ強化', desc: '悩み明示・CTA・タイトル改善' },
    { id: 'sns', label: '🔥 SNS拡散最適化', desc: '名言化・読了価値・ハッシュタグ' },
    { id: 'seo', label: '🔍 SEO最適化', desc: 'キーワード・要約・FAQ追加' },
    { id: 'readability', label: '📖 読みやすさ改善', desc: '段落分割・平易化・構成整理' },
    { id: 'title', label: '✍️ タイトル強化', desc: '5案提案・冒頭反映' },
  ];

  const handleImprove = async (instructionType, useCustom = false) => {
    if (!title && !content) {
      showStatus('改善する記事がありません', 'error');
      return;
    }
    setImproving(true);
    setShowImproveMenu(false);
    setShowCustomPrompt(false);
    showStatus('Geminiが記事を改善中...', 'info');
    try {
      const result = await improvePost({
        title,
        content,
        instructionType: useCustom ? 'custom' : instructionType,
        customPrompt: useCustom ? customPrompt : '',
      });
      if (result.success) {
        setTitle(result.title);
        setContent(result.content);
        showStatus('✨ AI改善が完了しました！', 'success');
      } else {
        showStatus(`改善失敗: ${result.error}`, 'error');
      }
    } catch (err) {
      const msg = err.response?.data?.error || '改善に失敗しました';
      showStatus(msg, 'error');
    } finally {
      setImproving(false);
      setCustomPrompt('');
    }
  };

  const handleOptimizeAll = async () => {
    if (!title && !content) {
      showStatus('最適化する記事がありません', 'error');
      return;
    }
    setOptimizing(true);
    setShowToolMenu(false);
    showStatus('自動最適化を実行中...', 'info');
    try {
      const result = await optimizeAllPost({ title, content });
      if (result.success) {
        setTitle(result.title);
        setContent(result.content);
        showStatus('✨ 自動最適化が完了しました！', 'success');
      } else {
        showStatus(`最適化失敗: ${result.error}`, 'error');
      }
    } catch (err) {
      const msg = err.response?.data?.error || '最適化に失敗しました';
      showStatus(msg, 'error');
    } finally {
      setOptimizing(false);
    }
  };

  const handleSearch = async (e) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;

    setIsSearching(true);
    try {
      const result = await searchAcrossBlogs(searchQuery);
      setSearchResults(result.results || []);
      if (result.results?.length === 0) {
        showStatus('見つかりませんでした', 'info');
      }
    } catch (err) {
      console.error(err);
      showStatus('検索に失敗しました', 'error');
    } finally {
      setIsSearching(false);
    }
  };

  const handleSearchResultClick = async (result) => {
    // 該当するブログに切り替え
    setSelectedBlogId(result.blog_id);
    setShowSearchPanel(false);
    setShowPostPanel(true);
    // 対象記事をセットするため、一覧から探すかAPI経由で取得済みのものを探す
    // getPostsの完了を待ってから該当記事を開くアプローチが確実
    try {
      const postsData = await getPosts(result.blog_id);
      const postList = postsData.posts || [];
      setPosts(postList);
      const post = postList.find(p => p.id === result.id);
      if (post) {
        loadPost(post);
        showStatus('記事を読み込みました', 'success');
      } else {
        // 直近一覧になかった場合は検索結果に含まれる本文を利用する
        loadPost({
          id: result.id,
          title: result.title,
          content: result.content || '(本文が取得できませんでした)',
          edit_link: result.edit_link,
          is_draft: result.is_draft
        });
        showStatus('過去記事を検索結果から読み込みました', 'success');
      }
    } catch (err) {
      showStatus('記事の読み込みに失敗しました', 'error');
    }
  };

  const handleBatchOptimize = async () => {
    if (batchSelected.length === 0) {
      showStatus('最適化する記事を選択してください', 'error');
      return;
    }
    setOptimizing(true);
    setBatchProgress(`0/${batchSelected.length} 完了`);
    showStatus(`一括最適化開始: ${batchSelected.length}件の記事を処理します`, 'info');
    let completed = 0;
    for (const post of batchSelected) {
      try {
        const result = await optimizeAllPost({ title: post.title, content: post.content || '' });
        if (result.success) {
          await savePost(selectedBlogId, {
            title: result.title,
            content: result.content,
            isDraft: post.is_draft,
            editLink: post.edit_link || '',
          });
          completed++;
          setBatchProgress(`${completed}/${batchSelected.length} 完了`);
          showStatus(`✅ ${completed}/${batchSelected.length} 完了: ${post.title}`, 'info');
        }
      } catch (err) {
        completed++;
        setBatchProgress(`${completed}/${batchSelected.length} 完了`);
        showStatus(`❌ 失敗: ${post.title} - ${err.response?.data?.error || err.message}`, 'error');
      }
      // Wait between requests to avoid 429
      await new Promise(r => setTimeout(r, 5000));
    }
    setOptimizing(false);
    setBatchProgress('');
    setBatchSelected([]);
    setBatchMode(false);
    showStatus(`✨ 一括最適化完了！ ${completed}件処理しました`, 'success');
    fetchPosts(selectedBlogId);
  };

  const handleRunTool = async (toolType) => {
    if (!title && !content) {
      showStatus('処理する記事がありません', 'error');
      return;
    }
    setRunningTool(true);
    setShowToolMenu(false);

    let result;
    try {
      if (toolType === 'affiliate') {
        showStatus('楽天APIで推薦商品を検索中...', 'info');
        result = await runToolAffiliate({ title, content });
      } else if (toolType === 'factcheck') {
        showStatus('リファレンスとリンクを整理中...', 'info');
        result = await runToolFactCheck({ title, content });
      } else if (toolType === 'thumbnail') {
        showStatus('AIサムネイルを生成・挿入中...', 'info');
        result = await generateThumbnail({ title, content });
      }

      if (result && result.success) {
        setContent(result.content);
        showStatus('✨ ツールの処理が完了しました！', 'success');
      } else {
        showStatus(`エラー: ${result?.error || '不明なエラー'}`, 'error');
      }
    } catch (err) {
      const msg = err.response?.data?.error || err.message || 'ツールの実行に失敗しました';
      showStatus(msg, 'error');
    } finally {
      setRunningTool(false);
    }
  };

  const handleCopy = async () => {
    const text = `${title}\n\n${content}`;
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      showStatus('クリップボードにコピーしました', 'success');
      setTimeout(() => setCopied(false), 2500);
    } catch {
      // フォールバック
      const el = document.createElement('textarea');
      el.value = text;
      document.body.appendChild(el);
      el.select();
      document.execCommand('copy');
      document.body.removeChild(el);
      setCopied(true);
      showStatus('クリップボードにコピーしました', 'success');
      setTimeout(() => setCopied(false), 2500);
    }
  };

  const loadPost = (post) => {
    setSelectedPost(post);
    setTitle(post.title);
    setContent(post.content || '');
    setIsDraft(post.is_draft);
    setShowPostPanel(false);
    showStatus(`「${post.title}」を読み込みました`, 'info');
  };

  const newPost = () => {
    setSelectedPost(null);
    setTitle('');
    setContent('');
    setIsDraft(true);
    setShowPostPanel(false);
  };

  const insertText = (text) => {
    const textarea = document.getElementById('main-editor');
    if (!textarea) return;
    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const newContent = content.substring(0, start) + text + content.substring(end);
    setContent(newContent);
    setTimeout(() => {
      textarea.focus();
      textarea.setSelectionRange(start + text.length, start + text.length);
    }, 0);
  };

  const handleInsertImage = () => {
    fileInputRef.current?.click();
  };

  const handleFileSelected = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    showStatus('Imgurにアップロード中...', 'info');
    try {
      const result = await uploadImage(file);
      if (result.success) {
        insertText(`![${file.name}](${result.url})`);
        showStatus('画像のアップロードが完了しました！', 'success');
      } else {
        showStatus(`アップロード失敗: ${result.error}`, 'error');
      }
    } catch (err) {
      showStatus('画像のアップロードに失敗しました', 'error');
    } finally {
      setUploading(false);
      e.target.value = '';
    }
  };

  const handleInsertYoutube = () => {
    const url = prompt('YouTube URLを入力してください:');
    if (url) {
      const id = url.match(/(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/watch\?v=|youtu\.be\/)([^& \n<]+)/)?.[1];
      if (id) {
        insertText(`[https://www.youtube.com/watch?v=${id}:embed]`);
        showStatus('YouTube リンクを挿入しました', 'info');
      } else {
        showStatus('有効なYouTube URLではありません', 'error');
      }
    }
  };

  const handleInsertAffiliate = () => {
    const html = '<!-- Affiliate Link Placeholder -->\n<div class="affiliate-box">ここにアフィリエイトHTMLを貼る</div>';
    insertText(html);
    showStatus('アフィリエイトテンプレートを挿入しました', 'info');
  };

  const handleSave = async (publish = false) => {
    if (!title.trim()) {
      showStatus('タイトルを入力してください', 'error');
      return;
    }
    setSaving(true);
    const saveDraft = !publish;
    try {
      const result = await savePost(selectedBlogId, {
        title,
        content,
        isDraft: saveDraft,
        editLink: selectedPost?.edit_link || '',
      });
      if (result.success) {
        const actionMsg = publish ? '公開しました！' : '下書きを保存しました！';
        showStatus(actionMsg, 'success');
        setIsDraft(saveDraft);
        // If newly created, store edit_link for future updates
        if (result.edit_link && !selectedPost) {
          setSelectedPost({ title, content, is_draft: saveDraft, edit_link: result.edit_link });
        }
        // Refresh post list
        fetchPosts(selectedBlogId);
      } else {
        showStatus(`保存失敗: ${result.error}`, 'error');
      }
    } catch (err) {
      const msg = err.response?.data?.error || err.message || '保存に失敗しました';
      showStatus(msg, 'error');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="h-screen flex items-center justify-center bg-background">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="w-8 h-8 animate-spin text-primary" />
          <p className="text-zinc-400 text-sm">読み込み中...</p>
        </div>
      </div>
    );
  }

  const currentBlog = blogs[selectedBlogId];

  return (
    <div className="flex h-screen bg-background text-foreground overflow-hidden">
      {/* Hidden file input for image upload */}
      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        className="hidden"
        onChange={handleFileSelected}
      />

      {/* Sidebar */}
      <aside className="w-72 border-r border-border flex flex-col glass z-10 transition-all duration-300">
        <div className="p-6 border-b border-border flex items-center gap-3">
          <div className="w-10 h-10 bg-primary rounded-xl flex items-center justify-center shadow-lg shadow-primary/20">
            <Layout className="w-6 h-6 text-white" />
          </div>
          <h1 className="text-xl font-bold tracking-tight">BlogSuite</h1>
        </div>

        <nav className="flex-1 overflow-y-auto p-4 space-y-2 custom-scrollbar">
          <p className="px-3 text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-2">My Blogs</p>
          {Object.entries(blogs).map(([id, blog]) => (
            <button
              key={id}
              onClick={() => setSelectedBlogId(id)}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium transition-all duration-200 group ${selectedBlogId === id
                ? 'bg-primary/10 text-primary border border-primary/20 shadow-sm'
                : 'text-zinc-400 hover:bg-zinc-800 hover:text-zinc-100'
                }`}
            >
              <div className={`w-2 h-2 rounded-full flex-shrink-0 ${selectedBlogId === id ? 'bg-primary animate-pulse' : 'bg-zinc-700 group-hover:bg-zinc-500'}`} />
              <span className="truncate text-left">{blog.blog_name}</span>
              <ChevronRight className={`ml-auto w-4 h-4 flex-shrink-0 transition-transform duration-200 ${selectedBlogId === id ? 'rotate-90 text-primary' : 'opacity-0 group-hover:opacity-100'}`} />
            </button>
          ))}
        </nav>

        <div className="p-4 border-t border-border space-y-2">
          <button
            onClick={() => { setShowSearchPanel(!showSearchPanel); setShowPostPanel(false); }}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium transition-all duration-200 ${showSearchPanel ? 'bg-zinc-800 text-white shadow-inner' : 'text-zinc-400 hover:bg-zinc-800 hover:text-white'}`}
          >
            <Search className="w-4 h-4" />
            <span>ブログ横断検索</span>
          </button>
          <button
            onClick={() => { newPost(); setShowSearchPanel(false); }}
            className="w-full flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium text-zinc-400 hover:bg-zinc-800 hover:text-white transition-all duration-200"
          >
            <PenSquare className="w-4 h-4" />
            <span>新規記事</span>
          </button>
          <button
            onClick={() => { setShowPostPanel(!showPostPanel); setShowSearchPanel(false); }}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium transition-all duration-200 ${showPostPanel && !showSearchPanel ? 'bg-zinc-800 text-white shadow-inner' : 'text-zinc-400 hover:bg-zinc-800 hover:text-white'}`}
          >
            <FileText className="w-4 h-4" />
            <span>記事一覧</span>
            {postsLoading && <Loader2 className="w-3 h-3 animate-spin ml-auto" />}
            {!postsLoading && posts.length > 0 && (
              <span className="ml-auto bg-zinc-700 text-xs py-0.5 px-2 rounded-full">{posts.length}</span>
            )}
          </button>
          <button className="w-full flex items-center gap-3 px-4 py-2 text-sm text-zinc-500 hover:text-white transition-colors">
            <Settings className="w-4 h-4" />
            <span>設定</span>
          </button>
        </div>
      </aside>

      {/* Global Search Panel */}
      {showSearchPanel && (
        <div className="w-96 border-r border-border glass z-20 flex flex-col animate-slide-in shadow-2xl">
          <div className="flex items-center justify-between p-4 border-b border-border">
            <h2 className="text-lg font-semibold flex items-center gap-2">
              <Globe className="w-5 h-5 text-zinc-400" />
              ブログ横断検索
            </h2>
            <button
              onClick={() => setShowSearchPanel(false)}
              className="p-2 hover:bg-zinc-800 rounded-lg text-zinc-400 hover:text-white transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          <div className="p-4 border-b border-border">
            <form onSubmit={handleSearch} className="flex gap-2">
              <input
                type="text"
                placeholder="キーワードを入力..."
                className="flex-1 bg-zinc-900 border border-zinc-700 rounded-xl px-4 py-2 text-sm text-white placeholder-zinc-500 focus:outline-none focus:border-violet-500 focus:ring-1 focus:ring-violet-500/50 transition-all"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
              <button
                type="submit"
                disabled={isSearching || !searchQuery.trim()}
                className="px-4 py-2 bg-primary hover:bg-primary/90 disabled:opacity-50 text-white rounded-xl text-sm font-medium transition-all flex items-center gap-2"
              >
                {isSearching ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
              </button>
            </form>
          </div>

          <div className="flex-1 overflow-y-auto custom-scrollbar p-2">
            {searchResults.length === 0 && !isSearching ? (
              <div className="text-center text-zinc-500 mt-10 text-sm">
                <Search className="w-8 h-8 mx-auto mb-3 opacity-20" />
                <p>全ブログから記事を検索します</p>
              </div>
            ) : (
              <div className="space-y-2">
                {searchResults.map((result) => (
                  <button
                    key={`${result.blog_id}-${result.id}`}
                    onClick={() => handleSearchResultClick(result)}
                    className="w-full text-left p-3 rounded-xl hover:bg-zinc-800/80 border border-transparent transition-all duration-200 group"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <span className={`text-[10px] px-1.5 py-0.5 rounded border ${result.is_draft ? 'text-yellow-400 border-yellow-500/20 bg-yellow-500/10' : 'text-green-400 border-green-500/20 bg-green-500/10'}`}>
                            {result.is_draft ? '下書き' : '公開'}
                          </span>
                          <span className="text-[10px] text-zinc-400 truncate bg-zinc-800 px-1.5 py-0.5 rounded">
                            {result.blog_name}
                          </span>
                        </div>
                        <span className="text-sm font-medium group-hover:text-primary transition-colors line-clamp-2 leading-snug">{result.title}</span>
                      </div>
                    </div>
                    {result.updated && (
                      <p className="text-xs text-zinc-500 mt-2 text-right">
                        {new Date(result.updated).toLocaleDateString('ja-JP')}
                      </p>
                    )}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Posts Panel (Slide-over) */}
      {showPostPanel && (
        <div className="fixed inset-0 z-50 flex">
          <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={() => setShowPostPanel(false)} />
          <div className="relative ml-72 w-96 h-full glass border-r border-border flex flex-col shadow-2xl">
            <div className="p-5 border-b border-border flex items-center justify-between">
              <div>
                <h3 className="font-semibold">記事一覧</h3>
                <p className="text-xs text-zinc-500 mt-0.5">{currentBlog?.blog_name}</p>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => { setBatchMode(!batchMode); setBatchSelected([]); }}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${batchMode ? 'bg-violet-600 text-white' : 'bg-zinc-800 text-zinc-400 hover:text-white'}`}
                >
                  {batchMode ? '選択中' : '一括選択'}
                </button>
                <button
                  onClick={() => fetchPosts(selectedBlogId)}
                  disabled={postsLoading}
                  className="p-2 hover:bg-white/5 rounded-lg transition-all"
                >
                  <RefreshCw className={`w-4 h-4 text-zinc-400 ${postsLoading ? 'animate-spin' : ''}`} />
                </button>
                <button onClick={() => { setShowPostPanel(false); setBatchMode(false); setBatchSelected([]); }} className="p-2 hover:bg-white/5 rounded-lg transition-all">
                  <X className="w-4 h-4 text-zinc-400" />
                </button>
              </div>
            </div>
            <div className="flex-1 overflow-y-auto p-4 space-y-2 custom-scrollbar">
              {postsLoading ? (
                <div className="flex justify-center pt-10">
                  <Loader2 className="w-6 h-6 animate-spin text-primary" />
                </div>
              ) : posts.length === 0 ? (
                <p className="text-zinc-500 text-sm text-center pt-10">記事がありません</p>
              ) : (
                posts.map((post, idx) => (
                  <div key={idx} className="flex items-start gap-2">
                    {batchMode && (
                      <input
                        type="checkbox"
                        checked={batchSelected.some(p => p.edit_link === post.edit_link)}
                        onChange={(e) => {
                          if (e.target.checked) {
                            setBatchSelected([...batchSelected, post]);
                          } else {
                            setBatchSelected(batchSelected.filter(p => p.edit_link !== post.edit_link));
                          }
                        }}
                        className="mt-4 w-4 h-4 rounded accent-violet-500 flex-shrink-0 cursor-pointer"
                      />
                    )}
                    <button
                      onClick={() => { if (!batchMode) loadPost(post); }}
                      className={`flex-1 text-left p-4 rounded-xl bg-zinc-800/50 hover:bg-zinc-700/60 border transition-all duration-200 group ${batchSelected.some(p => p.edit_link === post.edit_link) ? 'border-violet-500/40 bg-violet-900/20' : 'border-transparent hover:border-border'}`}
                    >
                      <div className="flex items-start gap-2">
                        {post.is_draft ? (
                          <EyeOff className="w-3.5 h-3.5 text-yellow-500 flex-shrink-0 mt-0.5" />
                        ) : (
                          <Eye className="w-3.5 h-3.5 text-green-500 flex-shrink-0 mt-0.5" />
                        )}
                        <span className="text-sm font-medium group-hover:text-primary transition-colors line-clamp-2">{post.title}</span>
                      </div>
                      <p className="text-xs text-zinc-500 mt-2 text-right">
                        {post.updated ? new Date(post.updated).toLocaleDateString('ja-JP') : ''}
                      </p>
                    </button>
                  </div>
                ))
              )}
            </div>
            <div className="p-4 border-t border-border space-y-2">
              {batchMode && batchSelected.length > 0 && (
                <button
                  onClick={handleBatchOptimize}
                  disabled={optimizing}
                  className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-gradient-to-r from-violet-600 to-purple-600 hover:from-violet-500 hover:to-purple-500 disabled:opacity-50 text-white rounded-xl text-sm font-semibold transition-all shadow-lg shadow-violet-500/20"
                >
                  {optimizing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
                  {optimizing ? batchProgress : `✨ ${batchSelected.length}件を一括最適化`}
                </button>
              )}
              {batchMode && (
                <button
                  onClick={() => {
                    if (batchSelected.length === posts.length) {
                      setBatchSelected([]);
                    } else {
                      setBatchSelected([...posts]);
                    }
                  }}
                  className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 border border-border rounded-xl text-xs font-medium transition-all"
                >
                  {batchSelected.length === posts.length ? '全解除' : '全選択'}
                </button>
              )}
              <button
                onClick={newPost}
                className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-primary/10 hover:bg-primary/20 text-primary border border-primary/20 rounded-xl text-sm font-medium transition-all duration-200"
              >
                <Plus className="w-4 h-4" />
                新規記事を作成
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Main Content */}
      <main className="flex-1 flex flex-col overflow-hidden">
        {/* Top Header */}
        <header className="h-20 border-b border-border flex items-center justify-between px-8 bg-background/50 backdrop-blur-sm z-10">
          <div>
            <h2 className="text-lg font-semibold flex items-center gap-2">
              {currentBlog?.blog_name || 'ブログを選択してください'}
              <span className="text-xs font-normal text-zinc-500 bg-zinc-800 px-2 py-0.5 rounded-full border border-border">
                {currentBlog?.hatena_blog_id}
              </span>
              {selectedPost && (
                <span className={`text-xs font-normal px-2 py-0.5 rounded-full border ${isDraft ? 'text-yellow-400 bg-yellow-500/10 border-yellow-500/20' : 'text-green-400 bg-green-500/10 border-green-500/20'}`}>
                  {isDraft ? '下書き' : '公開中'}
                </span>
              )}
            </h2>
            {selectedPost && (
              <p className="text-xs text-zinc-500 mt-0.5">編集中のURL: {selectedPost.edit_link ? '保存済み' : '新規記事'}</p>
            )}
          </div>
          <div className="flex items-center gap-3">
            {status.message && (
              <div className={`flex items-center gap-2 px-4 py-2 rounded-full text-xs font-medium animate-fade-in ${status.type === 'error' ? 'bg-red-500/10 text-red-400 border border-red-500/20' :
                status.type === 'success' ? 'bg-green-500/10 text-green-400 border border-green-500/20' :
                  'bg-blue-500/10 text-blue-400 border border-blue-500/20'
                }`}>
                {status.type === 'success' ? <CheckCircle className="w-3.5 h-3.5" /> : <AlertCircle className="w-3.5 h-3.5" />}
                {status.message}
              </div>
            )}
            {/* 安定版ツールボタン */}
            <div className="relative">
              <button
                onClick={() => { setShowToolMenu(!showToolMenu); setShowImproveMenu(false); }}
                disabled={runningTool || optimizing || improving}
                className="px-4 py-2.5 bg-zinc-800 hover:bg-zinc-700 disabled:opacity-50 text-white border border-border rounded-xl text-sm font-semibold transition-all duration-300 flex items-center gap-2 active:scale-95"
              >
                {runningTool ? <Loader2 className="w-4 h-4 animate-spin" /> : <Wrench className="w-4 h-4 text-emerald-400" />}
                {runningTool ? '処理中...' : 'ツール'}
                {!runningTool && <ChevronDown className={`w-3 h-3 transition-transform ${showToolMenu ? 'rotate-180' : ''}`} />}
              </button>
              {showToolMenu && (
                <div className="absolute right-0 top-full mt-2 w-64 glass rounded-2xl border border-border shadow-2xl z-50 overflow-hidden">
                  <div className="p-3 border-b border-border">
                    <p className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">安定版ツール (LLM非依存)</p>
                  </div>
                  <div className="p-2 space-y-1">
                    <button
                      onClick={() => handleRunTool('affiliate')}
                      className="w-full text-left px-4 py-3 rounded-xl hover:bg-emerald-500/10 hover:border-emerald-500/20 border border-transparent transition-all duration-150 group"
                    >
                      <div className="font-medium text-sm group-hover:text-emerald-400">🛒 楽天アフィリエイト追加</div>
                      <div className="text-xs text-zinc-500 mt-0.5">記事内容から楽天APIで商品を検索して追記</div>
                    </button>
                    <button
                      onClick={() => handleRunTool('factcheck')}
                      className="w-full text-left px-4 py-3 rounded-xl hover:bg-blue-500/10 hover:border-blue-500/20 border border-transparent transition-all duration-150 group"
                    >
                      <div className="font-medium text-sm group-hover:text-blue-400">✅ リンク・リファレンス整理</div>
                      <div className="text-xs text-zinc-500 mt-0.5">参考URLやリンク切れを自動で整理・修復</div>
                    </button>
                    <button
                      onClick={() => handleRunTool('thumbnail')}
                      className="w-full text-left px-4 py-3 rounded-xl hover:bg-purple-500/10 hover:border-purple-500/20 border border-transparent transition-all duration-150 group"
                    >
                      <div className="font-medium text-sm group-hover:text-purple-400">🖼️ AIサムネイル自動生成</div>
                      <div className="text-xs text-zinc-500 mt-0.5">記事タイトルと本文から自動で画像を生成・挿入</div>
                    </button>
                  </div>
                </div>
              )}
            </div>

            {/* AI改善ボタン */}
            <div className="relative">
              <button
                onClick={() => { setShowImproveMenu(!showImproveMenu); setShowToolMenu(false); setShowCustomPrompt(false); }}
                disabled={improving || optimizing || runningTool}
                className="px-4 py-2.5 bg-gradient-to-r from-violet-600 to-purple-600 hover:from-violet-500 hover:to-purple-500 disabled:opacity-50 text-white rounded-xl text-sm font-semibold transition-all duration-300 flex items-center gap-2 shadow-lg shadow-violet-500/20 active:scale-95"
              >
                {(improving || optimizing) ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
                {optimizing ? '一括最適化中...' : improving ? '改善中...' : 'AI改善'}
                {(!improving && !optimizing) && <ChevronDown className={`w-3 h-3 transition-transform ${showImproveMenu ? 'rotate-180' : ''}`} />}
              </button>
              {showImproveMenu && (
                <div className="absolute right-0 top-full mt-2 w-72 glass rounded-2xl border border-violet-500/20 shadow-2xl z-50 overflow-hidden">
                  <div className="p-3 border-b border-border">
                    <p className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">この記事をAI改善</p>
                  </div>
                  <div className="p-2 space-y-1">
                    {IMPROVE_PRESETS.map(preset => (
                      <button
                        key={preset.id}
                        onClick={() => handleImprove(preset.id)}
                        className="w-full text-left px-4 py-3 rounded-xl hover:bg-violet-500/10 hover:border-violet-500/20 border border-transparent transition-all duration-150 group"
                      >
                        <div className="font-medium text-sm group-hover:text-violet-300">{preset.label}</div>
                        <div className="text-xs text-zinc-500 mt-0.5">{preset.desc}</div>
                      </button>
                    ))}
                    <div className="w-full px-2 pt-1 pb-2">
                      <button
                        onClick={() => setShowCustomPrompt(!showCustomPrompt)}
                        className="w-full text-left px-4 py-3 rounded-xl hover:bg-zinc-700/50 border border-dashed border-zinc-700 hover:border-zinc-500 transition-all duration-150 text-sm text-zinc-400 hover:text-white"
                      >
                        ✏️ カスタム指示...
                      </button>
                      {showCustomPrompt && (
                        <div className="mt-2 space-y-2">
                          <textarea
                            value={customPrompt}
                            onChange={e => setCustomPrompt(e.target.value)}
                            placeholder="例：関西弁で書き直して"
                            className="w-full bg-zinc-900 border border-border rounded-lg p-3 text-sm resize-none h-24 focus:outline-none focus:border-violet-500 placeholder:text-zinc-700"
                          />
                          <button
                            onClick={() => handleImprove('custom', true)}
                            disabled={!customPrompt.trim()}
                            className="w-full py-2 bg-violet-600 hover:bg-violet-500 disabled:opacity-40 text-white rounded-lg text-sm font-medium transition-all"
                          >
                            この指示で改善
                          </button>
                        </div>
                      )}
                    </div>
                  </div>

                </div>
              )}
            </div>
            <button
              onClick={handleCopy}
              className="px-4 py-2.5 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 hover:text-white border border-border rounded-xl text-sm font-semibold transition-all duration-300 flex items-center gap-2 active:scale-95"
              title="タイトル＋本文をコピー"
            >
              {copied ? <ClipboardCheck className="w-4 h-4 text-green-400" /> : <Copy className="w-4 h-4" />}
              {copied ? 'コピー済み' : 'コピー'}
            </button>
            <button
              onClick={() => handleSave(false)}
              disabled={saving}
              className="px-5 py-2.5 bg-zinc-700 hover:bg-zinc-600 disabled:opacity-50 text-white rounded-xl text-sm font-semibold transition-all duration-300 flex items-center gap-2 active:scale-95"
            >
              {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
              下書き保存
            </button>
            <button
              onClick={() => handleSave(true)}
              disabled={saving}
              className="px-5 py-2.5 bg-primary hover:bg-blue-600 disabled:opacity-50 text-white rounded-xl text-sm font-semibold transition-all duration-300 flex items-center gap-2 shadow-lg shadow-primary/20 active:scale-95"
            >
              {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
              公開
            </button>
          </div>
        </header>

        {/* Editor Area */}
        <div className="flex-1 overflow-hidden flex flex-col p-8 max-w-5xl mx-auto w-full">
          <div className="mb-6 space-y-3">
            <input
              type="text"
              placeholder="記事タイトル..."
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="w-full bg-transparent text-4xl font-bold placeholder:text-zinc-800 focus:outline-none focus:ring-0 transition-all"
            />
            <div className="flex items-center gap-4 text-zinc-500 text-sm">
              <div className="flex items-center gap-2">
                <BookOpen className="w-4 h-4" />
                <span>{currentBlog?.blog_name || '—'}</span>
              </div>
              {selectedPost && (
                <span className="text-zinc-600">・ {selectedPost.updated ? new Date(selectedPost.updated).toLocaleDateString('ja-JP') : ''}</span>
              )}
              {!selectedPost && <span className="text-zinc-700">・ 新規記事</span>}
            </div>
          </div>

          <div className="flex-1 relative group overflow-hidden">
            <textarea
              id="main-editor"
              value={content}
              onChange={(e) => setContent(e.target.value)}
              placeholder="ここに記事を書いてください...&#10;&#10;はてな記法が使えます。&#10;例: *見出し、**太字**、[URL:title]"
              className="w-full h-full bg-transparent resize-none focus:outline-none text-base leading-relaxed placeholder:text-zinc-800 custom-scrollbar pb-24 font-mono"
            />

            {/* Action Bar (Floating at bottom of editor) */}
            <div className="absolute bottom-8 left-1/2 -translate-x-1/2 px-2 py-2 glass rounded-2xl flex items-center gap-1 shadow-2xl transition-all duration-300 transform group-hover:-translate-y-2">
              <button
                onClick={handleInsertImage}
                disabled={uploading}
                className="p-3 hover:bg-white/5 rounded-xl transition-all duration-200 group/btn disabled:opacity-50"
                title="Imgurに画像をアップロード"
              >
                {uploading
                  ? <Loader2 className="w-5 h-5 text-blue-400 animate-spin" />
                  : <ImageIcon className="w-5 h-5 text-zinc-400 group-hover/btn:text-blue-400" />
                }
              </button>
              <button
                onClick={handleInsertYoutube}
                className="p-3 hover:bg-white/5 rounded-xl transition-all duration-200 group/btn"
                title="YouTube動画を埋め込み"
              >
                <Youtube className="w-5 h-5 text-zinc-400 group-hover/btn:text-red-400" />
              </button>
              <button
                onClick={handleInsertAffiliate}
                className="p-3 hover:bg-white/5 rounded-xl transition-all duration-200 group/btn"
                title="アフィリエイトリンクを挿入"
              >
                <LinkIcon className="w-5 h-5 text-zinc-400 group-hover/btn:text-green-400" />
              </button>
              <div className="w-px h-6 bg-border mx-2" />
              <div className="flex items-center gap-2 px-3 py-2 text-xs text-zinc-500">
                <span>{content.length.toLocaleString()} 文字</span>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
};

export default App;
