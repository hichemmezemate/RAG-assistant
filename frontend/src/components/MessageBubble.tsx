import React, { Fragment } from 'react';
import { Message } from '../types';
import { SourceCitation } from './SourceCitation';
import { Bot, User, Award } from 'lucide-react';

interface Props {
  message: Message;
}

export const MessageBubble: React.FC<Props> = ({ message }) => {
  const isUser = message.role === 'User';

  const rawDate = message.createdAt || message.created_at || new Date().toISOString();
  const dateObj = new Date(rawDate);
  const formattedTime = !isNaN(dateObj.getTime())
    ? dateObj.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    : new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

  return (
    <div className={`message-row ${isUser ? 'message-user' : 'message-assistant'}`}>
      <div className="avatar-wrapper">
        {isUser ? (
          <div className="avatar avatar-user" title="Utilisateur">
            <User size={16} />
          </div>
        ) : (
          <div className="avatar avatar-assistant" title="Assistant RAG">
            <Bot size={16} />
          </div>
        )}
      </div>

      <div className="message-content-wrapper">
        <div className="message-bubble">
          <div className="message-text">
            {message.content.split('\n').map((line, idx) => (
              <Fragment key={idx}>
                {line}
                {idx < message.content.split('\n').length - 1 && <br />}
              </Fragment>
            ))}
          </div>

          {/* Sources citées si assistant */}
          {!isUser && message.sources && message.sources.length > 0 && (
            <SourceCitation sources={message.sources} />
          )}

          {/* Badge métriques qualité si disponible */}
          {!isUser && message.evaluation && (
            <div className="eval-badge" title="Métriques de qualité RAG">
              <Award size={12} className="eval-icon" />
              <span>
                Fidélité: {(message.evaluation.faithfulness * 100).toFixed(0)}% | Pertinence:{' '}
                {(message.evaluation.relevance * 100).toFixed(0)}%
              </span>
            </div>
          )}
        </div>

        <span className="message-timestamp">{formattedTime}</span>
      </div>
    </div>
  );
};
