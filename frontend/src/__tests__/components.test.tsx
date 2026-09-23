import React, { createRef } from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { SourceCitation } from '../components/SourceCitation';
import { MessageBubble } from '../components/MessageBubble';
import { DocumentUpload } from '../components/DocumentUpload';
import { ChatWindow } from '../components/ChatWindow';
import { Message, SourceCitation as SourceCitationType, Document } from '../types';

describe('Frontend Components', () => {
  describe('SourceCitation', () => {
    const mockSources: SourceCitationType[] = [
      {
        documentId: 'doc-1',
        documentName: 'convention_collective.pdf',
        pageOrSection: 'Article 12',
        extrait: 'La prime de fin d année est versée au mois de décembre.',
      },
    ];

    it('renders sources and expands excerpt on click', () => {
      render(<SourceCitation sources={mockSources} />);

      expect(screen.getByText(/Sources citées/i)).toBeInTheDocument();
      expect(screen.getByText('convention_collective.pdf')).toBeInTheDocument();
      expect(screen.getByText('Article 12')).toBeInTheDocument();

      // Click to toggle excerpt
      const toggleButton = screen.getByRole('button', { name: /convention_collective\.pdf/i });
      fireEvent.click(toggleButton);

      expect(screen.getByText(/La prime de fin d année est versée/i)).toBeInTheDocument();
    });

    it('returns null if sources list is empty', () => {
      const { container } = render(<SourceCitation sources={[]} />);
      expect(container.firstChild).toBeNull();
    });
  });

  describe('MessageBubble', () => {
    it('renders user message correctly', () => {
      const userMsg: Message = {
        id: '1',
        role: 'User',
        content: 'Bonjour, pouvez-vous m aider ?',
        createdAt: new Date().toISOString(),
      };

      render(<MessageBubble message={userMsg} />);
      expect(screen.getByText('Bonjour, pouvez-vous m aider ?')).toBeInTheDocument();
    });

    it('renders assistant message with sources and eval metrics', () => {
      const assistantMsg: Message = {
        id: '2',
        role: 'Assistant',
        content: 'Voici les détails selon le guide.',
        sources: [
          {
            documentId: '1',
            documentName: 'guide.pdf',
            extrait: 'Détails du guide',
            pageOrSection: 'Page 2',
          },
        ],
        createdAt: new Date().toISOString(),
        evaluation: {
          faithfulness: 0.95,
          relevance: 0.90,
          context_usage: 1.0,
        },
      };

      render(<MessageBubble message={assistantMsg} />);
      expect(screen.getByText('Voici les détails selon le guide.')).toBeInTheDocument();
      expect(screen.getByText('guide.pdf')).toBeInTheDocument();
      expect(screen.getByText(/Fidélité: 95%/i)).toBeInTheDocument();
    });
  });

  describe('DocumentUpload', () => {
    const mockDocs: Document[] = [
      {
        id: 'doc-1',
        filename: 'politique_rh.pdf',
        status: 'Indexed',
        uploadedAt: new Date().toISOString(),
      },
    ];

    it('renders documents list and calls onDelete when delete button clicked', () => {
      const handleDelete = jest.fn();
      const handleUpload = jest.fn();

      render(
        <DocumentUpload
          documents={mockDocs}
          uploading={false}
          onUpload={handleUpload}
          onDelete={handleDelete}
        />
      );

      expect(screen.getByText('politique_rh.pdf')).toBeInTheDocument();
      expect(screen.getByText('Indexé')).toBeInTheDocument();

      const deleteBtn = screen.getByTitle(/Supprimer le document/i);
      fireEvent.click(deleteBtn);
      expect(handleDelete).toHaveBeenCalledWith('doc-1');
    });
  });

  describe('ChatWindow', () => {
    it('disables send button when input is empty', () => {
      const handleSend = jest.fn();
      const ref = createRef<HTMLDivElement>();

      render(
        <ChatWindow
          messages={[]}
          loading={false}
          error={null}
          chatEndRef={ref}
          onSend={handleSend}
          onClearChat={jest.fn()}
          onClearError={jest.fn()}
        />
      );

      const sendBtn = screen.getByTitle('Envoyer la question');
      expect(sendBtn).toBeDisabled();

      const textarea = screen.getByPlaceholderText(/Posez votre question/i);
      fireEvent.change(textarea, { target: { value: 'Question pertinente' } });
      expect(sendBtn).not.toBeDisabled();

      fireEvent.click(sendBtn);
      expect(handleSend).toHaveBeenCalledWith('Question pertinente');
    });

    it('displays error banner when error exists', () => {
      const handleClearError = jest.fn();
      const ref = createRef<HTMLDivElement>();

      render(
        <ChatWindow
          messages={[]}
          loading={false}
          error="Échec de connexion au serveur"
          chatEndRef={ref}
          onSend={jest.fn()}
          onClearChat={jest.fn()}
          onClearError={handleClearError}
        />
      );

      expect(screen.getByText('Échec de connexion au serveur')).toBeInTheDocument();
      const closeBtn = screen.getByTitle("Fermer l'alerte");
      fireEvent.click(closeBtn);
      expect(handleClearError).toHaveBeenCalled();
    });

    it('renders reset button when messages exist and calls onClearChat on click', () => {
      const handleClearChat = jest.fn();
      const ref = createRef<HTMLDivElement>();
      const mockMessages: Message[] = [
        {
          id: '1',
          role: 'User',
          content: 'Bonjour',
          createdAt: new Date().toISOString(),
        },
      ];

      render(
        <ChatWindow
          messages={mockMessages}
          loading={false}
          error={null}
          chatEndRef={ref}
          onSend={jest.fn()}
          onClearChat={handleClearChat}
          onClearError={jest.fn()}
        />
      );

      const resetBtn = screen.getByTitle(/Effacer l'historique/i);
      expect(resetBtn).toBeInTheDocument();
      fireEvent.click(resetBtn);
      expect(handleClearChat).toHaveBeenCalledTimes(1);
    });
  });
});
