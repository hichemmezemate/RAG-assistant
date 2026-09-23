import React, { useState, FormEvent, KeyboardEvent } from 'react';
import { Message } from '../types';
import { MessageBubble } from './MessageBubble';
import { Send, Loader2, Sparkles, AlertCircle, X, RotateCcw } from 'lucide-react';

interface Props {
  messages: Message[];
  loading: boolean;
  error: string | null;
  chatEndRef: React.RefObject<HTMLDivElement>;
  onSend: (question: string) => void;
  onClearChat: () => void;
  onClearError: () => void;
}

export const ChatWindow: React.FC<Props> = ({
  messages,
  loading,
  error,
  chatEndRef,
  onSend,
  onClearChat,
  onClearError,
}) => {
  const [inputText, setInputText] = useState('');

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (inputText.trim() && !loading) {
      onSend(inputText);
      setInputText('');
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const isSendDisabled = !inputText.trim() || loading;

  return (
    <div className="chat-window-container">
      {/* Barre d'action supérieure si messages présents */}
      {messages.length > 0 && (
        <div className="chat-top-bar">
          <span className="chat-history-info">
            Conversation ({messages.length} message{messages.length > 1 ? 's' : ''})
          </span>
          <button
            type="button"
            className="btn-reset-chat"
            onClick={onClearChat}
            disabled={loading}
            title="Effacer l'historique et réinitialiser la discussion"
          >
            <RotateCcw size={13} />
            <span>Réinitialiser le chat</span>
          </button>
        </div>
      )}

      {/* Alertes d'erreur */}
      {error && (
        <div className="error-banner">
          <div className="error-text">
            <AlertCircle size={16} />
            <span>{error}</span>
          </div>
          <button
            type="button"
            className="btn-close-error"
            onClick={onClearError}
            title="Fermer l'alerte"
          >
            <X size={14} />
          </button>
        </div>
      )}

      {/* Zone des messages avec défilement */}
      <div className="chat-messages-area">
        {messages.length === 0 ? (
          <div className="empty-chat-placeholder">
            <div className="placeholder-icon">
              <Sparkles size={36} />
            </div>
            <h3>Bonjour ! Comment puis-je vous aider ?</h3>
            <p>
              Posez une question sur vos documents métier (procédures, règlements,
              notes internes) et obtenez une réponse précise avec les sources citées.
            </p>
          </div>
        ) : (
          messages.map((msg) => <MessageBubble key={msg.id} message={msg} />)
        )}

        {/* Indicateur de chargement / génération en cours */}
        {loading && (
          <div className="loading-indicator-row">
            <div className="avatar avatar-assistant">
              <Loader2 size={16} className="spinner" />
            </div>
            <div className="loading-bubble">
              <span className="pulsing-dot"></span>
              <span className="pulsing-dot"></span>
              <span className="pulsing-dot"></span>
              <span className="loading-label">Analyse du corpus et génération de la réponse...</span>
            </div>
          </div>
        )}

        {/* Ancre de scroll automatique */}
        <div ref={chatEndRef} />
      </div>

      {/* Formulaire de saisie */}
      <form className="chat-input-bar" onSubmit={handleSubmit}>
        <textarea
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Posez votre question sur les documents métier... (Entrée pour envoyer)"
          rows={1}
          disabled={loading}
          className="chat-textarea"
        />

        <button
          type="submit"
          disabled={isSendDisabled}
          className={`btn-send ${isSendDisabled ? 'btn-send-disabled' : ''}`}
          title="Envoyer la question"
        >
          {loading ? <Loader2 size={18} className="spinner" /> : <Send size={18} />}
        </button>
      </form>
    </div>
  );
};
