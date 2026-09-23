export type DocumentStatus = 'Processing' | 'Indexed' | 'Error';

export interface Document {
  id: string;
  filename: string;
  uploadedAt?: string;
  uploaded_at?: string;
  status: DocumentStatus;
}

export interface SourceCitation {
  documentId: string;
  documentName: string;
  pageOrSection?: string;
  extrait: string;
}

export type MessageRole = 'User' | 'Assistant';

export interface EvaluationResult {
  faithfulness: number;
  relevance: number;
  context_usage: number;
  details?: string;
}

export interface Message {
  id: string;
  role: MessageRole;
  content: string;
  sources?: SourceCitation[];
  createdAt?: string;
  created_at?: string;
  evaluation?: EvaluationResult;
}

export interface ChatState {
  messages: Message[];
  documents: Document[];
  loading: boolean;
  uploading: boolean;
  error: string | null;
}
