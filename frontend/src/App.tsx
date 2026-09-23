import React from 'react';
import { useChat } from './hooks/useChat';
import { DocumentUpload } from './components/DocumentUpload';
import { ChatWindow } from './components/ChatWindow';
import { Bot, Layers } from 'lucide-react';
import './App.css';

export const App: React.FC = () => {
  const {
    messages,
    documents,
    loading,
    uploading,
    error,
    chatEndRef,
    corpusStats,
    sendQuestion,
    uploadDoc,
    deleteDoc,
    clearChat,
    clearError,
  } = useChat();

  return (
    <div className="app-container">
      {/* Barre supérieure / Header */}
      <header className="app-header">
        <div className="brand">
          <div className="brand-icon">
            <Bot size={22} />
          </div>
          <div>
            <h1 className="brand-title">Assistant RAG Métier</h1>
            <p className="brand-subtitle">Documentation interne & Textes réglementaires</p>
          </div>
        </div>

        <div className="header-stats">
          <div className="stat-pill" title="Documents prêts à être interrogés">
            <Layers size={14} />
            <span>{corpusStats.indexedDocs} document{corpusStats.indexedDocs > 1 ? 's' : ''} indexé{corpusStats.indexedDocs > 1 ? 's' : ''}</span>
          </div>
        </div>
      </header>

      {/* Contenu principal en deux colonnes */}
      <main className="app-main">
        {/* Colonne latérale : Gestion du corpus */}
        <aside className="sidebar">
          <DocumentUpload
            documents={documents}
            uploading={uploading}
            onUpload={uploadDoc}
            onDelete={deleteDoc}
          />
        </aside>

        {/* Colonne centrale : Interface de chat RAG */}
        <section className="chat-section">
          <ChatWindow
            messages={messages}
            loading={loading}
            error={error}
            chatEndRef={chatEndRef}
            onSend={sendQuestion}
            onClearChat={clearChat}
            onClearError={clearError}
          />
        </section>
      </main>
    </div>
  );
};

export default App;
