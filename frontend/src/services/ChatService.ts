import { Document, Message } from '../types';

const API_BASE = '/api';

export class ChatService {
  /**
   * Fetch all indexed documents from the RAG corpus.
   */
  static async getDocuments(): Promise<Document[]> {
    const res = await fetch(`${API_BASE}/documents`);
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Échec de la récupération des documents' }));
      throw new Error(err.detail || 'Erreur lors du chargement des documents');
    }
    return res.json();
  }

  /**
   * Upload and index a new business document (.pdf, .docx, .txt).
   */
  static async uploadDocument(file: File): Promise<Document> {
    const formData = new FormData();
    formData.append('file', file);

    const res = await fetch(`${API_BASE}/documents`, {
      method: 'POST',
      body: formData,
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Échec de l'upload du document" }));
      throw new Error(err.detail || "Erreur lors de l'upload");
    }

    return res.json();
  }

  /**
   * Delete a document and its indexed chunks.
   */
  static async deleteDocument(id: string): Promise<void> {
    const res = await fetch(`${API_BASE}/documents/${id}`, {
      method: 'DELETE',
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Échec de la suppression du document' }));
      throw new Error(err.detail || 'Erreur lors de la suppression');
    }
  }

  /**
   * Ask a question to the assistant and retrieve the sourced answer.
   */
  static async sendMessage(question: string): Promise<Message> {
    const res = await fetch(`${API_BASE}/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ question }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Échec de génération de la réponse' }));
      throw new Error(err.detail || 'Erreur lors de la génération de réponse');
    }

    return res.json();
  }

  /**
   * Fetch the full conversation history.
   */
  static async getChatHistory(): Promise<Message[]> {
    const res = await fetch(`${API_BASE}/chat/history`);
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Échec de récupération de l'historique" }));
      throw new Error(err.detail || "Erreur lors du chargement de l'historique");
    }
    return res.json();
  }

  /**
   * Clear all conversation messages.
   */
  static async clearChatHistory(): Promise<void> {
    const res = await fetch(`${API_BASE}/chat/history`, {
      method: 'DELETE',
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Échec de la réinitialisation de l'historique" }));
      throw new Error(err.detail || 'Erreur lors de la réinitialisation');
    }
  }
}
