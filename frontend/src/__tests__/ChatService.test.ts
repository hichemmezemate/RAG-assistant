import { ChatService } from '../services/ChatService';

describe('ChatService', () => {
  beforeEach(() => {
    global.fetch = jest.fn();
  });

  afterEach(() => {
    jest.resetAllMocks();
  });

  it('fetches documents successfully', async () => {
    const mockDocs = [
      { id: '1', filename: 'doc1.pdf', uploadedAt: '2026-01-01', status: 'Indexed' },
    ];

    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => mockDocs,
    });

    const docs = await ChatService.getDocuments();
    expect(docs).toEqual(mockDocs);
    expect(global.fetch).toHaveBeenCalledWith('/api/documents');
  });

  it('sends chat message and receives response', async () => {
    const mockResponse = {
      id: 'msg-1',
      role: 'Assistant',
      content: 'Réponse avec source [Source: doc1.pdf]',
      sources: [
        { documentId: '1', documentName: 'doc1.pdf', extrait: 'Extrait', pageOrSection: 'Page 1' },
      ],
      createdAt: '2026-01-01T12:00:00Z',
    };

    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => mockResponse,
    });

    const result = await ChatService.sendMessage('Quelle est la procédure ?');
    expect(result).toEqual(mockResponse);
    expect(global.fetch).toHaveBeenCalledWith('/api/chat', expect.objectContaining({
      method: 'POST',
      body: JSON.stringify({ question: 'Quelle est la procédure ?' }),
    }));
  });

  it('deletes a document by id', async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ detail: 'Supprimé' }),
    });

    await expect(ChatService.deleteDocument('doc-123')).resolves.not.toThrow();
    expect(global.fetch).toHaveBeenCalledWith('/api/documents/doc-123', { method: 'DELETE' });
  });

  it('clears chat history', async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ detail: 'Historique réinitialisé' }),
    });

    await expect(ChatService.clearChatHistory()).resolves.not.toThrow();
    expect(global.fetch).toHaveBeenCalledWith('/api/chat/history', { method: 'DELETE' });
  });

  it('throws an error when request fails', async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: false,
      json: async () => ({ detail: 'Erreur serveur' }),
    });

    await expect(ChatService.sendMessage('test')).rejects.toThrow('Erreur serveur');
  });
});
