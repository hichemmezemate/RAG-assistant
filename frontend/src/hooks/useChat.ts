import { useState, useEffect, useRef, useMemo, useCallback } from 'react';
import { Document, Message } from '../types';
import { ChatService } from '../services/ChatService';

const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10 Mo
const ALLOWED_EXTENSIONS = ['.pdf', '.docx', '.txt'];

export function useChat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [uploading, setUploading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const chatEndRef = useRef<HTMLDivElement>(null);

  // Scroll automatique vers le dernier message
  const scrollToBottom = useCallback(() => {
    if (chatEndRef.current) {
      chatEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading, scrollToBottom]);

  // Chargement initial des documents et de l'historique
  useEffect(() => {
    let isMounted = true;

    async function initialize() {
      try {
        const [docs, history] = await Promise.all([
          ChatService.getDocuments().catch((err) => {
            console.warn('Documents initial load warning:', err);
            return [] as Document[];
          }),
          ChatService.getChatHistory().catch((err) => {
            console.warn('History initial load warning:', err);
            return [] as Message[];
          }),
        ]);

        if (isMounted) {
          setDocuments(docs);
          setMessages((prev) => (prev.length === 0 ? history : [...history, ...prev]));
        }
      } catch (err: any) {
        if (isMounted) {
          setError(err?.message || 'Erreur lors de la synchronisation initiale');
        }
      }
    }

    initialize();

    return () => {
      isMounted = false;
    };
  }, []);

  // useMemo pour calculer des statistiques sur le corpus
  const corpusStats = useMemo(() => {
    const totalDocs = documents.length;
    const indexedDocs = documents.filter((d) => d.status === 'Indexed').length;
    const processingDocs = documents.filter((d) => d.status === 'Processing').length;
    const errorDocs = documents.filter((d) => d.status === 'Error').length;
    return { totalDocs, indexedDocs, processingDocs, errorDocs };
  }, [documents]);

  // Envoi d'une question
  const sendQuestion = async (questionText: string) => {
    const trimmed = questionText.trim();
    if (!trimmed) {
      setError('La question ne peut pas être vide.');
      return;
    }

    setError(null);
    setLoading(true);

    // Message utilisateur optimiste
    const optimisticUserMessage: Message = {
      id: 'temp-' + Date.now(),
      role: 'User',
      content: trimmed,
      sources: [],
      createdAt: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, optimisticUserMessage]);

    try {
      const responseMessage = await ChatService.sendMessage(trimmed);
      setMessages((prev) => {
        // Remplacer ou ajouter la réponse assistant
        return [...prev, responseMessage];
      });
    } catch (err: any) {
      setError(err?.message || 'Erreur lors de la génération de la réponse.');
    } finally {
      setLoading(false);
    }
  };

  // Upload d'un document
  const uploadDoc = async (file: File) => {
    setError(null);

    // Validation du format
    const ext = '.' + file.name.split('.').pop()?.toLowerCase();
    if (!ALLOWED_EXTENSIONS.includes(ext)) {
      setError(`Format de fichier non supporté (${ext}). Formats autorisés : PDF, DOCX, TXT.`);
      return;
    }

    // Validation de la taille
    if (file.size > MAX_FILE_SIZE) {
      setError(`Fichier trop volumineux (${(file.size / (1024 * 1024)).toFixed(1)} Mo). Limite : 10 Mo.`);
      return;
    }

    setUploading(true);
    try {
      const newDoc = await ChatService.uploadDocument(file);
      setDocuments((prev) => [newDoc, ...prev.filter((d) => d.id !== newDoc.id)]);
    } catch (err: any) {
      setError(err?.message || "Erreur lors de l'upload du document.");
    } finally {
      setUploading(false);
    }
  };

  // Suppression d'un document
  const deleteDoc = async (id: string) => {
    setError(null);
    try {
      await ChatService.deleteDocument(id);
      setDocuments((prev) => prev.filter((d) => d.id !== id));
    } catch (err: any) {
      setError(err?.message || 'Erreur lors de la suppression du document.');
    }
  };

  // Réinitialisation de la conversation
  const clearChat = async () => {
    setError(null);
    try {
      await ChatService.clearChatHistory();
      setMessages([]);
    } catch (err: any) {
      setError(err?.message || "Erreur lors de la réinitialisation de l'historique.");
    }
  };

  const clearError = () => setError(null);

  return {
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
  };
}
