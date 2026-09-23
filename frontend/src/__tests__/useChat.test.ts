import { renderHook, act, waitFor } from '@testing-library/react';
import { useChat } from '../hooks/useChat';
import { ChatService } from '../services/ChatService';

jest.mock('../services/ChatService');

describe('useChat Hook', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (ChatService.getDocuments as jest.Mock).mockResolvedValue([]);
    (ChatService.getChatHistory as jest.Mock).mockResolvedValue([]);
  });

  it('initializes with empty lists and loads docs/history on mount', async () => {
    const mockDocs = [{ id: '1', filename: 'test.pdf', status: 'Indexed', uploadedAt: '2026-01-01' }];
    (ChatService.getDocuments as jest.Mock).mockResolvedValue(mockDocs);

    const { result } = renderHook(() => useChat());

    await waitFor(() => {
      expect(result.current.documents).toEqual(mockDocs);
    });
  });

  it('sends question and adds assistant response', async () => {
    const mockAssistantResponse = {
      id: 'resp-1',
      role: 'Assistant',
      content: 'Réponse générée',
      sources: [],
      createdAt: new Date().toISOString(),
    };
    (ChatService.sendMessage as jest.Mock).mockResolvedValue(mockAssistantResponse);

    const { result } = renderHook(() => useChat());

    await waitFor(() => {
      expect(ChatService.getDocuments).toHaveBeenCalled();
    });

    await act(async () => {
      await result.current.sendQuestion('Quelle est la politique ?');
    });

    expect(result.current.messages.length).toBe(2); // User + Assistant
    expect(result.current.messages[1].content).toBe('Réponse générée');
  });

  it('handles empty question error', async () => {
    const { result } = renderHook(() => useChat());

    await act(async () => {
      await result.current.sendQuestion('   ');
    });

    expect(result.current.error).toBe('La question ne peut pas être vide.');
  });

  it('clears chat history and empties messages list', async () => {
    (ChatService.clearChatHistory as jest.Mock).mockResolvedValue(undefined);

    const { result } = renderHook(() => useChat());

    await act(async () => {
      await result.current.clearChat();
    });

    expect(ChatService.clearChatHistory).toHaveBeenCalled();
    expect(result.current.messages).toEqual([]);
  });
});
