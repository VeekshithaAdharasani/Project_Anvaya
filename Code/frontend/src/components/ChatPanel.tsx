import React, { useState } from 'react';
import { sendChatMessage } from '../services/chatService';
import '../styles/chat.css'; // Load premium chat styles

interface Message {
    id: string;
    sender: 'user' | 'assistant';
    text: string;
    timestamp: Date;
}

interface ChatPanelProps {
    sessionId: string;
    onMessageSent?: () => void | Promise<void>;
}

export default function ChatPanel({ sessionId, onMessageSent }: ChatPanelProps) {
    const [messages, setMessages] = useState<Message[]>([]);
    const [inputText, setInputText] = useState('');
    const [loading, setLoading] = useState(false);
    const [status, setStatus] = useState('');

    const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
        event.preventDefault();
        const trimmedMessage = inputText.trim();
        if (!trimmedMessage || loading) {
            return;
        }

        const userMessageId = Math.random().toString(36).substring(7);
        const userMessage: Message = {
            id: userMessageId,
            sender: 'user',
            text: trimmedMessage,
            timestamp: new Date(),
        };

        // Append the user's message and clear input
        setMessages((prev) => [...prev, userMessage]);
        setInputText('');
        setLoading(true);
        setStatus('');

        try {
            const result = await sendChatMessage(sessionId, trimmedMessage);
            
            const assistantMessage: Message = {
                id: Math.random().toString(36).substring(7),
                sender: 'assistant',
                text: result.response,
                timestamp: new Date(),
            };
            
            setMessages((prev) => [...prev, assistantMessage]);
            setStatus('Message sent.');

            if (onMessageSent) {
                await onMessageSent();
            }
        } catch (error) {
            setStatus(error instanceof Error ? error.message : 'Unable to send chat message.');
        } finally {
            setLoading(false);
        }
    };

    const handleKeyDown = (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
        if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault();
            const form = event.currentTarget.form;
            if (form) {
                form.requestSubmit();
            }
        }
    };

    return (
        <div className="chat-panel-container">
            {/* Conversation History */}
            <div className="chat-history">
                {messages.length === 0 ? (
                    <div className="chat-empty-state">
                        <span className="chat-empty-icon">
                            <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.25" strokeLinecap="round" strokeLinejoin="round">
                                <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
                                <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
                            </svg>
                        </span>
                        <h4 className="chat-empty-title">Your journal is waiting.</h4>
                        <p className="chat-empty-text">
                            Tell me something about yourself, and together we'll write the next page.
                        </p>
                    </div>
                ) : (
                    messages.map((msg) => (
                        <div
                            key={msg.id}
                            className={`chat-message ${msg.sender === 'user' ? 'chat-message-user' : 'chat-message-assistant'}`}
                        >
                            {msg.text}
                        </div>
                    ))
                )}
            </div>

            {/* Reflection and Status Indicators */}
            {loading && (
                <div className="chat-status-bar">
                    <span className="chat-typing-indicator">
                        <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ marginRight: '4px' }}>
                            <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" />
                        </svg>
                        Anvaya is reflecting...
                    </span>
                </div>
            )}

            {status && !loading && (
                <div className="chat-status-bar">
                    <span>{status}</span>
                </div>
            )}

            {/* Input Form */}
            <form onSubmit={handleSubmit} className="chat-input-form">
                <textarea
                    value={inputText}
                    onChange={(e) => setInputText(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder="Share what's on your mind..."
                    disabled={loading}
                    rows={2}
                    className="chat-textarea"
                />
                <button
                    type="submit"
                    disabled={loading || !inputText.trim()}
                    className="chat-send-btn"
                >
                    {loading ? 'Reflecting...' : 'Send'}
                </button>
            </form>
        </div>
    );
}